from zope.interface import implements
from twisted.words import ewords
from twisted.cred import checkers, error, credentials
from twisted.python import failure
from twisted.internet import defer


# In memory storage and checking of nicknames/passwords
# If user name is not found, it adds the user to the database as unregistered
class DatabaseCredentialsChecker:
    """
    An extremely simple database credentials checker.
    """

    implements(checkers.ICredentialsChecker)

    credentialInterfaces = (credentials.IUsernamePassword,
                            credentials.IUsernameHashedPassword)

    def __init__(self, ctx):
        self.ctx = ctx

    def addUser(self, username):
        self.ctx["db"].createUser(username)

    def _cbPasswordMatch(self, matched, username):
        if matched:
            return username
        else:
            return failure.Failure(error.UnauthorizedLogin())

    def requestAvatarId(self, credentials):
        """
        Fetches the username of the profile that matches the given
        credentials. If the profile exists has a currently active session,
        authorization is denied. If the profile exists, has no active session,
        and is registered, the credentials are authenticated - on success the
        avatar name is returned. If the profile exists, has no current session,
        and is not registered, the avatar is returned (this allows annonymous
        users to take on other anonymous identities which are not being used).
        Finally, if the profile does not exist and profile creation is enabled,
        it is created and returned. All other cases result in a failure.
        """

        user = self.ctx["db"].lookupUser(credentials.username)
        if user:
            session = self.ctx.db.lookupUserSession(credentials.username)
            # If the session is active, fail - another user is connected
            # under these credentials. TODO: Add TTL
            if session and session["active"]:
                return defer.fail(ewords.AlreadyLoggedIn())

            # Registered user, session expired -> check password
            if user["registered"]:
                return defer.maybeDeferred(
                    credentials.checkPassword,
                    user["password"]).addCallback(
                        self._cbPasswordMatch, str(credentials.username))
            # Anonymous user, session expired (connection dropped hard) ->
            # grant login
            elif not user["registered"]:
                return str(credentials.username)
            else:
                defer.fail(error.UnauthorizedLogin())

        # User entry not found, check if we can create an anonymous
        elif self.ctx.user_on_request:
            # this may need to be changed if we use encrypted credentials
            self.addUser(credentials.username)
            return str(credentials.username)
        else:
            return defer.fail(error.UnauthorizedLogin())
