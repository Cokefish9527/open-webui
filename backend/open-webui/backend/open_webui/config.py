
####################################
# LDAP
####################################

ENABLE_LDAP = PersistentConfig(
    "ENABLE_LDAP",
    "ldap.enable",
    os.environ.get("ENABLE_LDAP", "false").lower() == "true",
)


####################################
# Single Sign-On (SSO)
####################################

ENABLE_SSO = PersistentConfig(
    "ENABLE_SSO",
    "auth.sso.enable",
    os.environ.get("ENABLE_SSO", "False").lower() == "true",
)

SSO_SESSION_LIMIT = PersistentConfig(
    "SSO_SESSION_LIMIT",
    "auth.sso.session_limit",
    int(os.environ.get("SSO_SESSION_LIMIT", "1")),
)

SSO_DISCONNECT_OLD_SESSIONS = PersistentConfig(
    "SSO_DISCONNECT_OLD_SESSIONS",
    "auth.sso.disconnect_old_sessions",
    os.environ.get("SSO_DISCONNECT_OLD_SESSIONS", "True").lower() == "true",
)
