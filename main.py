import logging
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.constants import ChatMemberStatus
import asyncio
from flask import Flask
import threading
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for Koyeb health checks
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Telegram Leave Bot is running! 🤖", 200

@app.route('/health')
def health():
    return {"status": "healthy", "service": "telegram-leave-bot"}, 200

class TelegramLeaveBot:
    def __init__(self, bot_token: str, group_chat_id: int):
        """
        Initialize the bot
        
        Args:
            bot_token: Your bot token from @BotFather
            group_chat_id: The chat ID of your group (negative number)
        """
        self.bot_token = bot_token
        self.group_chat_id = group_chat_id
        self.application = Application.builder().token(bot_token).build()
        
    async def handle_member_left(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle when a member leaves the group"""
        try:
            # Check if this update is from our target group
            if update.effective_chat.id != self.group_chat_id:
                return
                
            # Check if someone left the chat
            if update.message and update.message.left_chat_member:
                left_member = update.message.left_chat_member
                
                # Don't send message if bot itself left or if it's a bot
                if left_member.is_bot:
                    logger.info(f"Bot {left_member.username} left the group")
                    return
                    
                logger.info(f"Member {left_member.full_name} (@{left_member.username}) left the group")
                
                # Send private message to the user who left
                try:
                    await context.bot.send_message(
                        chat_id=left_member.id,
                        text=f"Hi {left_member.first_name}! 👋\n\n"
                             f"I noticed you left our group. We're sorry to see you go! 😢\n\n"
                             f"Would you mind sharing why you decided to leave? Your feedback would help us improve the group experience for everyone.\n\n"
                             f"Thanks for taking the time to let us know! 🙏"
                    )
                    logger.info(f"Successfully sent leave message to {left_member.full_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to send message to {left_member.full_name}: {e}")
                    # This usually happens when the user has blocked the bot or disabled messages from unknown contacts
                    
        except Exception as e:
            logger.error(f"Error in handle_member_left: {e}")
    
    async def handle_chat_member_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle chat member status updates (alternative method)"""
        try:
            if not update.chat_member or update.effective_chat.id != self.group_chat_id:
                return
                
            old_status = update.chat_member.old_chat_member.status
            new_status = update.chat_member.new_chat_member.status
            user = update.chat_member.new_chat_member.user
            
            # Check if member left (was member/admin/owner, now left/kicked)
            if (old_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] and 
                new_status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]):
                
                if user.is_bot:
                    return
                    
                logger.info(f"Member {user.full_name} (@{user.username}) status changed from {old_status} to {new_status}")
                
                try:
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=f"Hi {user.first_name}! 👋\n\n"
                             f"I noticed you left our group. We're sorry to see you go! 😢\n\n"
                             f"Would you mind sharing why you decided to leave? Your feedback would help us improve the group experience for everyone.\n\n"
                             f"Thanks for taking the time to let us know! 🙏"
                    )
                    logger.info(f"Successfully sent leave message to {user.full_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to send message to {user.full_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in handle_chat_member_update: {e}")
    
    def setup_handlers(self):
        """Setup message handlers"""
        # Handler for left_chat_member messages
        self.application.add_handler(
            MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_member_left)
        )
        
        # Handler for chat member updates (more reliable)
        self.application.add_handler(
            MessageHandler(filters.StatusUpdate.CHAT_MEMBER, self.handle_chat_member_update)
        )
    
    async def start_bot(self):
        """Start the bot using webhooks for Koyeb"""
        self.setup_handlers()
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(allowed_updates=["message", "chat_member"])
        logger.info("Bot started successfully!")

def run_flask():
    """Run Flask server in a separate thread"""
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)

async def main():
    """Main function to run the bot"""
    
    # Debug: Print all environment variables (for troubleshooting)
    logger.info("Available environment variables:")
    for key in sorted(os.environ.keys()):
        if 'TOKEN' in key or 'CHAT' in key or 'BOT' in key:
            logger.info(f"  {key}: {'*' * len(str(os.environ[key]))}")
        elif key in ['PORT', 'PYTHONPATH']:
            logger.info(f"  {key}: {os.environ[key]}")
    
    # Get configuration from environment variables
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    GROUP_CHAT_ID = os.environ.get('GROUP_CHAT_ID')
    
    logger.info(f"BOT_TOKEN found: {bool(BOT_TOKEN)}")
    logger.info(f"GROUP_CHAT_ID found: {bool(GROUP_CHAT_ID)}")
    
    # Validate configuration
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN environment variable is required!")
        logger.error("Set it in Koyeb environment variables")
        logger.error("Available env vars: " + str(list(os.environ.keys())))
        return
        
    if not GROUP_CHAT_ID:
        logger.error("❌ GROUP_CHAT_ID environment variable is required!")
        logger.error("Set it in Koyeb environment variables (should be a negative number)")
        return
    
    try:
        group_chat_id = int(GROUP_CHAT_ID)
    except ValueError:
        logger.error("❌ GROUP_CHAT_ID must be a valid integer!")
        return
    
    # Start Flask server in background thread for Koyeb health checks
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"Flask server started on port {os.environ.get('PORT', 8000)}")
    
    # Create and run the bot
    bot = TelegramLeaveBot(BOT_TOKEN, group_chat_id)
    
    logger.info("🤖 Telegram Leave Detection Bot for Koyeb")
    logger.info("=" * 50)
    logger.info(f"Bot Token: {BOT_TOKEN[:10]}...")
    logger.info(f"Group Chat ID: {group_chat_id}")
    logger.info("=" * 50)
    logger.info("✅ Bot is starting...")
    
    try:
        await bot.start_bot()
        # Keep the bot running
        while True:
            await asyncio.sleep(60)  # Check every minute
            logger.info("Bot is running...")
            
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Error running bot: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
