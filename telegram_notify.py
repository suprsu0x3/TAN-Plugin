#!/usr/bin/env python3

import json
import os
from typing import Any, override
import requests

from sqlalchemy.orm import Session
from empire.server.core.hooks import hooks
from empire.server.core.db import models
from empire.server.core.plugins import BasePlugin

class Plugin(BasePlugin):
    def on_agent_connect(self, db: Session, agent: models.Agent):
        """
        print to the console whenever an agent checks in.
        """

        self.currentSettings = self.current_settings(db)

        msg = self.currentSettings["message_template"]
        msg = msg.replace("<agent_name>", agent.name)
        msg = msg.replace("<agent_ip>", agent.external_ip)
        msg = msg.replace("<agent_user>", agent.username)
        msg = msg.replace("<agent_os>", agent.os_details)
        msg = msg.replace("<process_name>", agent.process_name)

        msg = msg.replace("\\n", "\n")

        chatids = self.currentSettings["telegram_chat_id"].replace(" ", "").split(",")
        for chatid in chatids:
            self.send_telegram_notification(msg, self.currentSettings["telegram_token"], chatid )


    @override
    def on_load(self, db):
        """
        Called when the plugin is loaded
        """

        self.execution_enabled = False
        self.settings_options = {
            "telegram_token": {
                "Description": "Bot token for Telegram notifications.",
                "Value": "BOT TOKEN",
                "Required": True
            },
            "telegram_chat_id": {
                "Description": "Chat ID to send notifications to.",
                "Value": "CHAT_ID1, CHAT_ID2,",
                "Required": True
            },
            "message_template": {
                "type": "string",
                "Description": "Notification message template",
                "Required": True,
                "Value": "🦅 New Agent Connected!\nAgent: <agent_name>\nIP: <agent_ip>\nUser: <agent_user>\nOS: <agent_os>\nProcess: <process_name>",
            },   
        }
       
    @override
    def on_start(self, db):
        """
        Called when the plugin is enabled
        """

        self.send_socketio_message(f'Telegram Agent Alert plugin enabled')
        hooks.register_hook(hooks.AFTER_AGENT_CHECKIN_HOOK, 'checkin_logger_hook', self.on_agent_connect)

    @override
    def on_stop(self, db):
        """
        Called when the plugin is disabled
        """
        self.send_socketio_message(f'Telegram Agent Alert plugin disabled')
        hooks.unregister_hook('checkin_logger_hook', hooks.AFTER_AGENT_CHECKIN_HOOK)


    @override
    def execute(self, command, **kwargs):   
        pass

    def send_telegram_notification(self, message: str, bot_token: str, chat_id: str):
        """Send notification via Telegram"""
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            
            # Run in thread pool since requests is blocking
            response = requests.post(url, json=payload, timeout=10)
            
            response.raise_for_status()
            
        except Exception as e:
            print()
            self.send_socketio_message(f"TAN Error: {str(e)}")



def initialize(main_menu):
    """
    Initialize the plugin
    """
    return Plugin(main_menu)