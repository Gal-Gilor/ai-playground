"""Outlook Graph API Skill for Claude Code.

This module provides enterprise-grade integration with Microsoft Graph API
for Outlook mailbox operations including authentication, email management,
and search capabilities.

Author: Claude Code
Version: 1.0.0
License: MIT
"""

from outlook_graph_skill.auth.authenticator import GraphAuthenticator
from outlook_graph_skill.mailbox.email_client import EmailClient
from outlook_graph_skill.config.settings import SkillConfig

__version__ = "1.0.0"
__all__ = ["GraphAuthenticator", "EmailClient", "SkillConfig"]
