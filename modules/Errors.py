class Base(Exception):
    """Custom Base for all exceptions"""
    def __init__(self, original_error: Exception, message: str):
        self.original_error = original_error
        self.message = message

class ManageGuild(Base):
    """Raises when bot is missing the "manage guild" permission"""

class ManageWebhooks(Base):
    """Raises when bot is missing the "manage webhooks" permission"""

class ManageChannels(Base):
    """Raises when bot is missing the "manage channels" permission"""

class ManageThreads(Base):
    """Raises when bot is missing the "manage threads" permission"""

class ManageEvents(Base):
    """Raises when bot is missing the "manage events" permission"""

class ManageRoles(Base):
    """Raises when bot is missing the "manage roles" permission"""

class ManageMessages(Base):
    """Raises when bot is missing the "manage messages" permission"""

class ManageEmojisAndStickers(Base):
    """Raises whn bot is missing the "manage emojis and stickers" permission"""

class ReadMessageHistory(Base):
    """Raises when bot is missing the "read message history" permission"""

class SendMessages(Base):
    """Raises when bot is missing the "send messages" permission"""

class SendMessagesInThreads(Base):
    """Raises when bot is missing the "send messages in threads" permission"""

class CreatePublicThreads(Base):
    """Raises when bot is missing the "create public threads" permission"""

class CreatePrivateThreads(Base):
    """Raises when bot is missing the "create private threads" permission"""

class ViewAuditLog(Base):
    """Raises when bot is missing the "view audit log" permission"""

class CreateInstantInvite(Base):
    """Raises when bot is missing the "create invites" permission"""

class BanMembers(Base):
    """Raises when bot is missing the "ban members" permission"""

class KickMembers(Base):
    """Raises when bot is missing the "kick members" permission"""

class MoveMembers(Base):
    """Raises when bot is missing the "move members" permission"""

class ModerateMembers(Base):
    """Raises when bot is missing the "moderate members" permission"""



