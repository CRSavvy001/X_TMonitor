import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
)
from twitter_monitor import TwitterMonitor
from config import TELEGRAM_BOT_TOKEN, TWITTER_API_KEY, CHECK_INTERVAL
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Storage file for watched accounts
WATCHED_FILE = "watched_accounts.json"

def load_watched_accounts():
    """Load watched accounts from JSON"""
    if Path(WATCHED_FILE).exists():
        with open(WATCHED_FILE, "r") as f:
            return json.load(f)
    return {}

def save_watched_accounts(data):
    """Save watched accounts to JSON"""
    with open(WATCHED_FILE, "w") as f:
        json.dump(data, f, indent=2)

class TwitterBot:
    def __init__(self, token, api_key):
        self.app = Application.builder().token(token).build()
        self.monitor = TwitterMonitor(api_key)
        self.watched = load_watched_accounts()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Register command handlers"""
        self.app.add_handler(CommandHandler("watch", self.watch))
        self.app.add_handler(CommandHandler("unwatch", self.unwatch))
        self.app.add_handler(CommandHandler("watching", self.watching))
        self.app.add_handler(CommandHandler("start", self.start))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command"""
        await update.message.reply_text(
            "🐦 <b>X Monitor Bot</b>\n\n"
            "/watch &lt;url&gt; - Monitor a Twitter handle\n"
            "/unwatch &lt;url&gt; - Stop monitoring\n"
            "/watching - List active monitors",
            parse_mode="HTML"
        )
    
    async def watch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add a handle to watch"""
        if not context.args or not context.args[0].startswith("https://x.com/"):
            await update.message.reply_text(
                "❌ Usage: /watch https://x.com/handle"
            )
            return
        
        url = context.args[0]
        handle = self.monitor.get_handle_from_url(url)
        chat_id = str(update.effective_chat.id)
        
        if chat_id not in self.watched:
            self.watched[chat_id] = {}
        
        # Get baseline (latest tweet)
        latest = self.monitor.get_latest_tweet(handle)
        baseline_id = latest.get("id") if latest else None
        
        self.watched[chat_id][handle] = {
            "url": url,
            "last_tweet_id": baseline_id,
            "added_at": datetime.now().isoformat()
        }
        save_watched_accounts(self.watched)
        
        await update.message.reply_text(
            f"✅ Now monitoring @{handle}"
        )
        
        # Start monitoring job
        context.job_queue.run_repeating(
            self.check_tweets,
            interval=CHECK_INTERVAL,
            first=CHECK_INTERVAL,
            data={"chat_id": chat_id, "handle": handle}
        )
    
    async def unwatch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove a handle from watch"""
        if not context.args:
            await update.message.reply_text("❌ Usage: /unwatch https://x.com/handle")
            return
        
        url = context.args[0]
        handle = self.monitor.get_handle_from_url(url)
        chat_id = str(update.effective_chat.id)
        
        if chat_id in self.watched and handle in self.watched[chat_id]:
            del self.watched[chat_id][handle]
            save_watched_accounts(self.watched)
            await update.message.reply_text(f"✅ Stopped monitoring @{handle}")
        else:
            await update.message.reply_text(f"❌ Not monitoring @{handle}")
    
    async def watching(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all watched handles"""
        chat_id = str(update.effective_chat.id)
        
        if chat_id not in self.watched or not self.watched[chat_id]:
            await update.message.reply_text("📭 Not monitoring any handles")
            return
        
        handles = list(self.watched[chat_id].keys())
        text = "👁️ <b>Monitoring:</b>\n\n" + "\n".join([f"• @{h}" for h in handles])
        await update.message.reply_text(text, parse_mode="HTML")
    
    async def check_tweets(self, context: ContextTypes.DEFAULT_TYPE):
        """Background job to check for new tweets"""
        data = context.job.data
        chat_id = data["chat_id"]
        handle = data["handle"]
        
        if chat_id not in self.watched or handle not in self.watched[chat_id]:
            context.job.schedule_removal()
            return
        
        try:
            latest = self.monitor.get_latest_tweet(handle)
            if not latest:
                return
            
            last_id = self.watched[chat_id][handle].get("last_tweet_id")
            current_id = latest.get("id")
            
            # New tweet detected
            if current_id != last_id and last_id is not None:
                formatted = self.monitor.format_tweet(latest)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=formatted,
                    parse_mode="HTML"
                )
            
            # Update baseline
            self.watched[chat_id][handle]["last_tweet_id"] = current_id
            save_watched_accounts(self.watched)
        
        except Exception as e:
            logger.error(f"Error checking tweets for {handle}: {e}")
    
    def run(self):
        """Start the bot"""
        self.app.run_polling()

if __name__ == "__main__":
    from datetime import datetime
    bot = TwitterBot(TELEGRAM_BOT_TOKEN, TWITTER_API_KEY)
    logger.info("Bot started")
    bot.run()
