from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.core.database import Base


class GmailCredential(Base):
    """
    Stores OAuth tokens for a user's connected Gmail account.
    One row per user (UNIQUE on user_id).
    Access / refresh tokens are stored encrypted at rest via Fernet.
    """
    __tablename__ = "gmail_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )

    gmail_email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Fernet-encrypted token blobs (see gmail_service.py for encrypt/decrypt)
    encrypted_access_token:  Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, nullable=False)

    # ISO 8601 expiry — used to decide whether to refresh before API calls
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Space-separated OAuth scopes granted by the user
    scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Whether to include this account in the periodic sync job
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Set after each successful sync run
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Last error message from sync (None = last sync was clean)
    sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
