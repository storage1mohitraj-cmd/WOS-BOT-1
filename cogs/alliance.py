import discord
from discord import app_commands
from discord.ext import commands
import sqlite3  
import asyncio
from datetime import datetime
from discord.ext import tasks
from typing import List, Dict, Optional
import os
from .login_handler import LoginHandler
try:
    from db.mongo_adapters import mongo_enabled, AdminsAdapter, AlliancesAdapter, AllianceSettingsAdapter, AllianceMembersAdapter
except Exception as import_error:
    # Fallback: If MongoDB adapters fail to import, use SQLite exclusively
    print(f"[WARNING] MongoDB adapters import failed: {import_error}. Using SQLite fallback.")
    mongo_enabled = lambda: False
    
    # Provide dummy adapter classes that always return None/False
    class AdminsAdapter:
        @staticmethod
        def get(user_id): return None
        @staticmethod
        def upsert(user_id, is_initial): return False
        @staticmethod
        def count(): return 0
    
    class AlliancesAdapter:
        @staticmethod
        def get_all(): return []
        @staticmethod
        def get(alliance_id): return None
    
    class AllianceSettingsAdapter:
        @staticmethod
        def get(alliance_id): return None
    
    class AllianceMembersAdapter:
        @staticmethod
        def get_all_members(): return []


# Import database utilities for consistent path handling
try:
    from db_utils import get_db_connection
except ImportError:
    # Fallback if db_utils is not available
    from pathlib import Path
    def get_db_connection(db_name: str, **kwargs):
        repo_root = Path(__file__).resolve().parents[1]
        db_dir = repo_root / "db"
        db_dir.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(db_dir / db_name), **kwargs)

class Alliance(commands.Cog):
    def __init__(self, bot, conn):
        self.bot = bot
        self.conn = conn
        self.c = self.conn.cursor()
        
        # Use centralized database connection utility for consistent paths
        self.conn_users = get_db_connection('users.sqlite')
        self.c_users = self.conn_users.cursor()
        
        self.conn_settings = get_db_connection('settings.sqlite')
        self.c_settings = self.conn_settings.cursor()
        
        self.conn_giftcode = get_db_connection('giftcode.sqlite')
        self.c_giftcode = self.conn_giftcode.cursor()

        self._create_table()
        self._check_and_add_column()

        # Alliance Monitoring Initialization
        self.login_handler = LoginHandler()
        
        # Level mapping for furnace levels
        self.level_mapping = {
            31: "30-1", 32: "30-2", 33: "30-3", 34: "30-4",
            35: "FC 1", 36: "FC 1-1", 37: "FC 1-2", 38: "FC 1-3", 39: "FC 1-4",
            40: "FC 2", 41: "FC 2-1", 42: "FC 2-2", 43: "FC 2-3", 44: "FC 2-4",
            45: "FC 3", 46: "FC 3-1", 47: "FC 3-2", 48: "FC 3-3", 49: "FC 3-4",
            50: "FC 4", 51: "FC 4-1", 52: "FC 4-2", 53: "FC 4-3", 54: "FC 4-4",
            55: "FC 5", 56: "FC 5-1", 57: "FC 5-2", 58: "FC 5-3", 59: "FC 5-4",
            60: "FC 6", 61: "FC 6-1", 62: "FC 6-2", 63: "FC 6-3", 64: "FC 6-4",
            65: "FC 7", 66: "FC 7-1", 67: "FC 7-2", 68: "FC 7-3", 69: "FC 7-4",
            70: "FC 8", 71: "FC 8-1", 72: "FC 8-2", 73: "FC 8-3", 74: "FC 8-4",
            75: "FC 9", 76: "FC 9-1", 77: "FC 9-2", 78: "FC 9-3", 79: "FC 9-4",
            80: "FC 10", 81: "FC 10-1", 82: "FC 10-2", 83: "FC 10-3", 84: "FC 10-4"
        }
        
        # Furnace level emojis
        self.fl_emojis = {
            range(35, 40): "<:fc1:1326751863764156528>",
            range(40, 45): "<:fc2:1326751886954594315>",
            range(45, 50): "<:fc3:1326751903912034375>",
            range(50, 55): "<:fc4:1326751938674692106>",
            range(55, 60): "<:fc5:1326751952750776331>",
            range(60, 65): "<:fc6:1326751966184869981>",
            range(65, 70): "<:fc7:1326751983939489812>",
            range(70, 75): "<:fc8:1326751996707082240>",
            range(75, 80): "<:fc9:1326752008505528331>",
            range(80, 85): "<:fc10:1326752023001174066>"
        }
        
        # Logging
        self.log_directory = 'log'
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)
        self.log_file = os.path.join(self.log_directory, 'alliance_monitoring.txt')
        
        # Initialize monitoring tables
        self._initialize_monitoring_tables()
        
        # Start background monitoring task
        self.monitor_alliances.start()
    
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.monitor_alliances.cancel()

    def _create_table(self):
        # Core alliance list
        self.c.execute("""
            CREATE TABLE IF NOT EXISTS alliance_list (
                alliance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                discord_server_id INTEGER
            )
        """)

        # Settings for alliances (may be stored in SQLite for legacy/partial flows)
        try:
            self.c.execute("""
                CREATE TABLE IF NOT EXISTS alliancesettings (
                    alliance_id INTEGER PRIMARY KEY,
                    channel_id INTEGER,
                    interval INTEGER DEFAULT 0
                )
            """)
        except Exception:
            # Best-effort: if creating this table fails, other code will handle exceptions
            pass

        # Ensure legacy/local DB tables used elsewhere exist (best-effort).
        try:
            # giftcode DB tables
            self.c_giftcode.execute("""
                CREATE TABLE IF NOT EXISTS giftcodecontrol (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alliance_id INTEGER,
                    status INTEGER
                )
            """)

            self.c_giftcode.execute("""
                CREATE TABLE IF NOT EXISTS giftcode_channel (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alliance_id INTEGER,
                    channel_id INTEGER
                )
            """)
        except Exception:
            pass

        try:
            # users table (minimal shape to allow counts/queries)
            self.c_users.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fid TEXT,
                    nickname TEXT,
                    furnace_lv INTEGER DEFAULT 0,
                    kid INTEGER,
                    stove_lv_content TEXT,
                    alliance INTEGER
                )
            """)
        except Exception:
            pass

        try:
            # settings DB: admin + adminserver used by settings flow
            self.c_settings.execute("""
                CREATE TABLE IF NOT EXISTS admin (
                    id INTEGER PRIMARY KEY,
                    is_initial INTEGER DEFAULT 0
                )
            """)
            self.c_settings.execute("""
                CREATE TABLE IF NOT EXISTS adminserver (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alliances_id INTEGER
                )
            """)
        except Exception:
            pass

        # Commit all changes where possible
        try:
            self.conn.commit()
        except Exception:
            pass
        try:
            self.conn_giftcode.commit()
        except Exception:
            pass
        try:
            self.conn_users.commit()
        except Exception:
            pass
        try:
            self.conn_settings.commit()
        except Exception:
            pass

    def _check_and_add_column(self):
        self.c.execute("PRAGMA table_info(alliance_list)")
        columns = [info[1] for info in self.c.fetchall()]
        if "discord_server_id" not in columns:
            self.c.execute("ALTER TABLE alliance_list ADD COLUMN discord_server_id INTEGER")
            self.conn.commit()

    def _get_admin(self, user_id):
        """Get admin info with MongoDB fallback to SQLite"""
        try:
            if mongo_enabled():
                admin = AdminsAdapter.get(user_id)
                if admin is not None:
                    return admin
                # If MongoDB returns None, fall back to SQLite
        except Exception as e:
            print(f"[WARNING] MongoDB AdminsAdapter.get failed: {e}. Falling back to SQLite.")
        
        # SQLite fallback
        try:
            self.c_settings.execute("SELECT id, is_initial FROM admin WHERE id = ?", (user_id,))
            return self.c_settings.fetchone()
        except Exception as e:
            print(f"[ERROR] SQLite admin query failed: {e}")
            return None

    def _upsert_admin(self, user_id, is_initial=1):
        """Insert/update admin with MongoDB fallback to SQLite"""
        success = False
        try:
            if mongo_enabled():
                success = AdminsAdapter.upsert(user_id, is_initial)
                if success:
                    return True
                # If MongoDB fails, fall back to SQLite
                print(f"[WARNING] MongoDB AdminsAdapter.upsert returned False. Falling back to SQLite.")
        except Exception as e:
            print(f"[WARNING] MongoDB AdminsAdapter.upsert failed: {e}. Falling back to SQLite.")
        
        # SQLite fallback
        try:
            self.c_settings.execute(
                "INSERT OR REPLACE INTO admin (id, is_initial) VALUES (?, ?)",
                (user_id, is_initial)
            )
            self.conn_settings.commit()
            return True
        except Exception as e:
            print(f"[ERROR] SQLite admin upsert failed: {e}")
            return False

    def _count_admins(self):
        """Count admins with MongoDB fallback to SQLite"""
        try:
            if mongo_enabled():
                count = AdminsAdapter.count()
                if count is not None and count >= 0:
                    return count
                # If MongoDB returns None, fall back to SQLite
        except Exception as e:
            print(f"[WARNING] MongoDB AdminsAdapter.count failed: {e}. Falling back to SQLite.")
        
        # SQLite fallback
        try:
            self.c_settings.execute("SELECT COUNT(*) FROM admin")
            return self.c_settings.fetchone()[0]
        except Exception as e:
            print(f"[ERROR] SQLite admin count failed: {e}")
            return 0


    async def view_alliances(self, interaction: discord.Interaction):
        
        if interaction.guild is None:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ This command must be used in a server, not in DMs.", ephemeral=True)
            else:
                await interaction.followup.send("❌ This command must be used in a server, not in DMs.", ephemeral=True)
            return

        user_id = interaction.user.id
        if mongo_enabled():
            admin = AdminsAdapter.get(user_id)
        else:
            self.c_settings.execute("SELECT id, is_initial FROM admin WHERE id = ?", (user_id,))
            admin = self.c_settings.fetchone()

        if admin is None:
            if not interaction.response.is_done():
                await interaction.response.send_message("You do not have permission to view alliances.", ephemeral=True)
            else:
                await interaction.followup.send("You do not have permission to view alliances.", ephemeral=True)
            return

        is_initial = admin[1] if isinstance(admin, tuple) else int(admin.get('is_initial', 0))
        guild_id = interaction.guild.id

        try:
            if mongo_enabled():
                docs = AlliancesAdapter.get_all()
                if is_initial == 1:
                    alliances = [(d['alliance_id'], d['name'], (AllianceSettingsAdapter.get(d['alliance_id']) or {}).get('interval', 0)) for d in docs]
                else:
                    alliances = [(d['alliance_id'], d['name'], (AllianceSettingsAdapter.get(d['alliance_id']) or {}).get('interval', 0)) for d in docs if int(d.get('discord_server_id') or 0) == guild_id]
            else:
                if is_initial == 1:
                    query = """
                        SELECT a.alliance_id, a.name, COALESCE(s.interval, 0) as interval
                        FROM alliance_list a
                        LEFT JOIN alliancesettings s ON a.alliance_id = s.alliance_id
                        ORDER BY a.alliance_id ASC
                    """
                    self.c.execute(query)
                else:
                    query = """
                        SELECT a.alliance_id, a.name, COALESCE(s.interval, 0) as interval
                        FROM alliance_list a
                        LEFT JOIN alliancesettings s ON a.alliance_id = s.alliance_id
                        WHERE a.discord_server_id = ?
                        ORDER BY a.alliance_id ASC
                    """
                    self.c.execute(query, (guild_id,))
                alliances = self.c.fetchall()

            alliance_list = ""
            for alliance_id, name, interval in alliances:
                
                if mongo_enabled():
                    try:
                        members = AllianceMembersAdapter.get_all_members()
                        member_count = sum(1 for m in members if int(m.get('alliance', 0)) == alliance_id)
                    except Exception:
                        member_count = 0
                else:
                    self.c_users.execute("SELECT COUNT(*) FROM users WHERE alliance = ?", (alliance_id,))
                    member_count = self.c_users.fetchone()[0]
                
                interval_text = f"{interval} minutes" if interval > 0 else "No automatic control"
                alliance_list += f"🛡️ **{alliance_id}: {name}**\n👥 Members: {member_count}\n⏱️ Control Interval: {interval_text}\n\n"

            if not alliance_list:
                alliance_list = "No alliances found."

            embed = discord.Embed(
                title="Existing Alliances",
                description=alliance_list,
                color=discord.Color.blue()
            )
            try:
                await interaction.response.defer(ephemeral=True)
            except Exception:
                pass
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An error occurred while fetching alliances.", 
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "An error occurred while fetching alliances.", 
                    ephemeral=True
                )

    async def alliance_autocomplete(self, interaction: discord.Interaction, current: str):
        self.c.execute("SELECT alliance_id, name FROM alliance_list")
        alliances = self.c.fetchall()
        return [
            app_commands.Choice(name=f"{name} (ID: {alliance_id})", value=str(alliance_id))
            for alliance_id, name in alliances if current.lower() in name.lower()
        ][:25]

    @app_commands.command(name="settings", description="Open settings menu.")
    async def settings(self, interaction: discord.Interaction):
        try:
            if interaction.guild is not None: # Check bot permissions only if in a guild
                perm_check = interaction.guild.get_member(interaction.client.user.id)
                if not perm_check.guild_permissions.administrator:
                    await interaction.response.send_message(
                        "Beeb boop 🤖 I need **Administrator** permissions to function. "
                        "Go to server settings --> Roles --> find my role --> scroll down and turn on Administrator", 
                        ephemeral=True
                    )
                    return
                
            # Use helper method with automatic fallback
            admin_count = self._count_admins()
            user_id = interaction.user.id

            if admin_count == 0:
                # First time setup - make this user the global admin
                self._upsert_admin(user_id, 1)

                first_use_embed = discord.Embed(
                    title="🎉 First Time Setup",
                    description=(
                        "This command has been used for the first time and no administrators were found.\n\n"
                        f"**{interaction.user.name}** has been added as the Global Administrator.\n\n"
                        "You can now access all administrative functions."
                    ),
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=first_use_embed, ephemeral=True)
                
                await asyncio.sleep(3)
                
            # Use helper method with automatic fallback
            admin = self._get_admin(user_id)

            if admin is None:
                # User is not in database - check if they have Discord admin permissions
                if interaction.guild and (interaction.user.guild_permissions.administrator or interaction.guild.owner_id == interaction.user.id):
                    # Grant admin rights automatically
                    self._upsert_admin(user_id, 1)
                    admin = self._get_admin(user_id)
                else:
                    await interaction.response.send_message(
                        "You do not have permission to access this menu.", 
                        ephemeral=True
                    )
                    return

            embed = discord.Embed(
                title="⚙️ Settings Menu",
                description=(
                    "Please select a category:\n\n"
                    "**Menu Categories**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🏰 **Alliance Operations**\n"
                    "└ Manage alliances and settings\n\n"
                    "👥 **Alliance Member Operations**\n"
                    "└ Add, remove, and view members\n\n"
                    "🤖 **Bot Operations**\n"
                    "└ Configure bot settings\n\n"
                    "🎁 **Gift Code Operations**\n"
                    "└ Manage gift codes and rewards\n\n"
                    "📜 **Alliance History**\n"
                    "└ View alliance changes and history\n\n"
                    "🆘 **Support Operations**\n"
                    "└ Access support features\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=discord.Color.blue()
            )
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="Alliance Operations",
                emoji="🏰",
                style=discord.ButtonStyle.primary,
                custom_id="alliance_operations",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label="Member Operations",
                emoji="👥",
                style=discord.ButtonStyle.primary,
                custom_id="member_operations",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label="Bot Operations",
                emoji="🤖",
                style=discord.ButtonStyle.primary,
                custom_id="bot_operations",
                row=1
            ))
            view.add_item(discord.ui.Button(
                label="Gift Operations",
                emoji="🎁",
                style=discord.ButtonStyle.primary,
                custom_id="gift_code_operations",
                row=1
            ))
            view.add_item(discord.ui.Button(
                label="Alliance History",
                emoji="📜",
                style=discord.ButtonStyle.primary,
                custom_id="alliance_history",
                row=2
            ))
            view.add_item(discord.ui.Button(
                label="Support Operations",
                emoji="🆘",
                style=discord.ButtonStyle.primary,
                custom_id="support_operations",
                row=2
            ))
            view.add_item(discord.ui.Button(
                label="Other Features",
                emoji="🔧",
                style=discord.ButtonStyle.primary,
                custom_id="other_features",
                row=3
            ))

            if admin_count == 0:
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                await interaction.response.send_message(embed=embed, view=view)

        except Exception as e:
            if not any(error_code in str(e) for error_code in ["10062", "40060"]):
                print(f"Settings command error: {e}")
            error_message = "An error occurred while processing your request."
            if not interaction.response.is_done():
                await interaction.response.send_message(error_message, ephemeral=True)
            else:
                await interaction.followup.send(error_message, ephemeral=True)





    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id")
            user_id = interaction.user.id
            
            # Use helper method with automatic fallback
            admin = self._get_admin(user_id)
            is_admin = admin is not None
            is_initial = int(admin[1]) if (admin and isinstance(admin, tuple)) else (int(admin.get('is_initial', 0)) if admin else 0)

            # If user is not recognized as admin, attempt to grant if they have Discord admin rights
            if not is_admin:
                if interaction.guild and (interaction.user.guild_permissions.administrator or interaction.guild.owner_id == interaction.user.id):
                    # Grant admin rights in the DB using helper method
                    self._upsert_admin(user_id, 1)
                    is_initial = 1
                    # Refresh admin status after insertion
                    admin = self._get_admin(user_id)
                    is_admin = admin is not None
                else:
                    await interaction.response.send_message("You do not have permission to perform this action.", ephemeral=True)
                    return

            try:
                if custom_id == "alliance_operations":
                    embed = discord.Embed(
                        title="🏰 Alliance Operations",
                        description=(
                            "Please select an operation:\n\n"
                            "**Available Operations**\n"
                            "━━━━━━━━━━━━━━━━━━━━━━\n"
                            "➕ **Add Alliance**\n"
                            "└ Create a new alliance\n\n"
                            "✏️ **Edit Alliance**\n"
                            "└ Modify existing alliance settings\n\n"
                            "🗑️ **Delete Alliance**\n"
                            "└ Remove an existing alliance\n\n"
                            "👀 **View Alliances**\n"
                            "└ List all available alliances\n"
                            "━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=discord.Color.blue()
                    )
                    
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(
                        label="Add Alliance", 
                        emoji="➕",
                        style=discord.ButtonStyle.success, 
                        custom_id="add_alliance", 
                        disabled=is_initial != 1
                    ))
                    view.add_item(discord.ui.Button(
                        label="Edit Alliance", 
                        emoji="✏️",
                        style=discord.ButtonStyle.primary, 
                        custom_id="edit_alliance", 
                        disabled=is_initial != 1
                    ))
                    view.add_item(discord.ui.Button(
                        label="Delete Alliance", 
                        emoji="🗑️",
                        style=discord.ButtonStyle.danger, 
                        custom_id="delete_alliance", 
                        disabled=is_initial != 1
                    ))
                    view.add_item(discord.ui.Button(
                        label="View Alliances", 
                        emoji="👀",
                        style=discord.ButtonStyle.primary, 
                        custom_id="view_alliances"
                    ))
                    view.add_item(discord.ui.Button(
                        label="Check Alliance", 
                        emoji="🔍",
                        style=discord.ButtonStyle.primary, 
                        custom_id="check_alliance"
                    ))
                    view.add_item(discord.ui.Button(
                        label="Main Menu", 
                        emoji="🏠",
                        style=discord.ButtonStyle.secondary, 
                        custom_id="main_menu"
                    ))

                    await interaction.response.edit_message(embed=embed, view=view)

                elif custom_id == "edit_alliance":
                    if is_initial != 1:
                        await interaction.response.send_message("You do not have permission to perform this action.", ephemeral=True)
                        return
                    await self.edit_alliance(interaction)

                elif custom_id == "check_alliance":
                    self.c.execute("""
                        SELECT a.alliance_id, a.name, COALESCE(s.interval, 0) as interval
                        FROM alliance_list a
                        LEFT JOIN alliancesettings s ON a.alliance_id = s.alliance_id
                        ORDER BY a.name
                    """)
                    alliances = self.c.fetchall()

                    if not alliances:
                        await interaction.response.send_message("No alliances found to check.", ephemeral=True)
                        return

                    options = [
                        discord.SelectOption(
                            label="Check All Alliances",
                            value="all",
                            description="Start control process for all alliances",
                            emoji="🔄"
                        )
                    ]
                    
                    options.extend([
                        discord.SelectOption(
                            label=f"{name[:40]}",
                            value=str(alliance_id),
                            description=f"Control Interval: {interval} minutes"
                        ) for alliance_id, name, interval in alliances
                    ])

                    select = discord.ui.Select(
                        placeholder="Select an alliance to check",
                        options=options,
                        custom_id="alliance_check_select"
                    )

                    async def alliance_check_callback(select_interaction: discord.Interaction):
                        try:
                            selected_value = select_interaction.data["values"][0]
                            control_cog = self.bot.get_cog('Control')
                            
                            if not control_cog:
                                await select_interaction.response.send_message("Control module not found.", ephemeral=True)
                                return
                            
                            # Ensure the centralized queue processor is running
                            await control_cog.login_handler.start_queue_processor()
                            
                            if selected_value == "all":
                                progress_embed = discord.Embed(
                                    title="🔄 Alliance Control Queue",
                                    description=(
                                        "**Control Queue Information**\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"📊 **Total Alliances:** `{len(alliances)}`\n"
                                        "🔄 **Status:** `Adding alliances to control queue...`\n"
                                        "⏰ **Queue Start:** `Now`\n"
                                        "⚠️ **Note:** `Each alliance will be processed in sequence`\n"
                                        "⏱️ **Wait Time:** `1 minute between each alliance control`\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                        "⌛ Please wait while alliances are being processed..."
                                    ),
                                    color=discord.Color.blue()
                                )
                                await select_interaction.response.send_message(embed=progress_embed)
                                msg = await select_interaction.original_response()
                                message_id = msg.id

                                # Queue all alliance operations at once
                                queued_alliances = []
                                for index, (alliance_id, name, _) in enumerate(alliances):
                                    try:
                                        self.c.execute("""
                                            SELECT channel_id FROM alliancesettings WHERE alliance_id = ?
                                        """, (alliance_id,))
                                        channel_data = self.c.fetchone()
                                        channel = self.bot.get_channel(channel_data[0]) if channel_data else select_interaction.channel
                                        
                                        await control_cog.login_handler.queue_operation({
                                            'type': 'alliance_control',
                                            'callback': lambda ch=channel, aid=alliance_id, inter=select_interaction: control_cog.check_agslist(ch, aid, interaction=inter),
                                            'description': f'Manual control check for alliance {name}',
                                            'alliance_id': alliance_id,
                                            'interaction': select_interaction
                                        })
                                        queued_alliances.append((alliance_id, name))
                                    
                                    except Exception as e:
                                        print(f"Error queuing alliance {name}: {e}")
                                        continue
                                
                                # Update status to show all alliances have been queued
                                queue_status_embed = discord.Embed(
                                    title="🔄 Alliance Control Queue",
                                    description=(
                                        "**Control Queue Information**\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"📊 **Total Alliances Queued:** `{len(queued_alliances)}`\n"
                                        f"⏰ **Queue Start:** <t:{int(datetime.now().timestamp())}:R>\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                        "⌛ All alliance controls have been queued and will process in order..."
                                    ),
                                    color=discord.Color.blue()
                                )
                                channel = select_interaction.channel
                                msg = await channel.fetch_message(message_id)
                                await msg.edit(embed=queue_status_embed)
                                
                                # Monitor queue completion
                                start_time = datetime.now()
                                while True:
                                    queue_info = control_cog.login_handler.get_queue_info()
                                    
                                    # Check if all our operations are done
                                    if queue_info['queue_size'] == 0 and queue_info['current_operation'] is None:
                                        # Double-check by waiting a moment
                                        await asyncio.sleep(2)
                                        queue_info = control_cog.login_handler.get_queue_info()
                                        if queue_info['queue_size'] == 0 and queue_info['current_operation'] is None:
                                            break
                                    
                                    # Update status periodically
                                    if queue_info['current_operation'] and queue_info['current_operation'].get('type') == 'alliance_control':
                                        current_alliance_id = queue_info['current_operation'].get('alliance_id')
                                        current_name = next((name for aid, name in queued_alliances if aid == current_alliance_id), "Unknown")
                                        
                                        update_embed = discord.Embed(
                                            title="🔄 Alliance Control Queue",
                                            description=(
                                                "**Control Queue Information**\n"
                                                "━━━━━━━━━━━━━━━━━━━━━━\n"
                                                f"📊 **Total Alliances:** `{len(queued_alliances)}`\n"
                                                f"🔄 **Currently Processing:** `{current_name}`\n"
                                                f"📈 **Queue Remaining:** `{queue_info['queue_size']}`\n"
                                                f"⏰ **Started:** <t:{int(start_time.timestamp())}:R>\n"
                                                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                                "⌛ Processing controls..."
                                            ),
                                            color=discord.Color.blue()
                                        )
                                        await msg.edit(embed=update_embed)
                                    
                                    await asyncio.sleep(5)  # Check every 5 seconds
                                
                                # All operations complete
                                queue_complete_embed = discord.Embed(
                                    title="✅ Alliance Control Queue Complete",
                                    description=(
                                        "**Queue Status Information**\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"📊 **Total Alliances Processed:** `{len(queued_alliances)}`\n"
                                        "🔄 **Status:** `All controls completed`\n"
                                        f"⏰ **Completion Time:** <t:{int(datetime.now().timestamp())}:R>\n"
                                        f"⏱️ **Total Duration:** `{int((datetime.now() - start_time).total_seconds())} seconds`\n"
                                        "📝 **Note:** `Control results have been shared in respective channels`\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━"
                                    ),
                                    color=discord.Color.green()
                                )
                                await msg.edit(embed=queue_complete_embed)
                            
                            else:
                                alliance_id = int(selected_value)
                                self.c.execute("""
                                    SELECT a.name, s.channel_id 
                                    FROM alliance_list a
                                    LEFT JOIN alliancesettings s ON a.alliance_id = s.alliance_id
                                    WHERE a.alliance_id = ?
                                """, (alliance_id,))
                                alliance_data = self.c.fetchone()

                                if not alliance_data:
                                    await select_interaction.response.send_message("Alliance not found.", ephemeral=True)
                                    return

                                alliance_name, channel_id = alliance_data
                                channel = self.bot.get_channel(channel_id) if channel_id else select_interaction.channel
                                
                                status_embed = discord.Embed(
                                    title="🔍 Alliance Control",
                                    description=(
                                        "**Control Information**\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"📊 **Alliance:** `{alliance_name}`\n"
                                        f"🔄 **Status:** `Queued`\n"
                                        f"⏰ **Queue Time:** `Now`\n"
                                        f"📢 **Results Channel:** `{channel.name if channel else 'Designated channel'}`\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                        "⏳ Alliance control will begin shortly..."
                                    ),
                                    color=discord.Color.blue()
                                )
                                await select_interaction.response.send_message(embed=status_embed)
                                
                                await control_cog.login_handler.queue_operation({
                                    'type': 'alliance_control',
                                    'callback': lambda ch=channel, aid=alliance_id: control_cog.check_agslist(ch, aid),
                                    'description': f'Manual control check for alliance {alliance_name}',
                                    'alliance_id': alliance_id
                                })

                        except Exception as e:
                            print(f"Alliance check error: {e}")
                            await select_interaction.response.send_message(
                                "An error occurred during the control process.", 
                                ephemeral=True
                            )

                    select.callback = alliance_check_callback
                    view = discord.ui.View()
                    view.add_item(select)

                    embed = discord.Embed(
                        title="🔍 Alliance Control",
                        description=(
                            "Please select an alliance to check:\n\n"
                            "**Information**\n"
                            "━━━━━━━━━━━━━━━━━━━━━━\n"
                            "• Select 'Check All Alliances' to process all alliances\n"
                            "• Control process may take a few minutes\n"
                            "• Results will be shared in the designated channel\n"
                            "• Other controls will be queued during the process\n"
                            "━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=discord.Color.blue()
                    )
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

                elif custom_id == "member_operations":
                    await self.bot.get_cog("AllianceMemberOperations").handle_member_operations(interaction)

                elif custom_id == "bot_operations":
                    try:
                        bot_ops_cog = interaction.client.get_cog("BotOperations")
                        if bot_ops_cog:
                            await bot_ops_cog.show_bot_operations_menu(interaction)
                        else:
                            await interaction.response.send_message(
                                "❌ Bot Operations module not found.",
                                ephemeral=True
                            )
                    except Exception as e:
                        if not any(error_code in str(e) for error_code in ["10062", "40060"]):
                            print(f"Bot operations error: {e}")
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                "An error occurred while loading Bot Operations.",
                                ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                "An error occurred while loading Bot Operations.",
                                ephemeral=True
                            )

                elif custom_id == "gift_code_operations":
                    try:
                        gift_ops_cog = interaction.client.get_cog("GiftOperations")
                        if gift_ops_cog:
                            await gift_ops_cog.show_gift_menu(interaction)
                        else:
                            await interaction.response.send_message(
                                "❌ Gift Operations module not found.",
                                ephemeral=True
                            )
                    except Exception as e:
                        print(f"Gift operations error: {e}")
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                "An error occurred while loading Gift Operations.",
                                ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                "An error occurred while loading Gift Operations.",
                                ephemeral=True
                            )

                elif custom_id == "add_alliance":
                    if not is_admin:
                        await interaction.response.send_message("You do not have permission to perform this action.", ephemeral=True)
                        return
                    await self.add_alliance(interaction)

                elif custom_id == "delete_alliance":
                    if not is_admin:
                        await interaction.response.send_message("You do not have permission to perform this action.", ephemeral=True)
                        return
                    await self.delete_alliance(interaction)

                elif custom_id == "view_alliances":
                    await self.view_alliances(interaction)

                elif custom_id == "support_operations":
                    try:
                        support_ops_cog = interaction.client.get_cog("SupportOperations")
                        if support_ops_cog:
                            await support_ops_cog.show_support_menu(interaction)
                        else:
                            await interaction.response.send_message(
                                "❌ Support Operations module not found.",
                                ephemeral=True
                            )
                    except Exception as e:
                        if not any(error_code in str(e) for error_code in ["10062", "40060"]):
                            print(f"Support operations error: {e}")
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                "An error occurred while loading Support Operations.", 
                                ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                "An error occurred while loading Support Operations.",
                                ephemeral=True
                            )

                elif custom_id == "alliance_history":
                    try:
                        changes_cog = interaction.client.get_cog("Changes")
                        if changes_cog:
                            await changes_cog.show_alliance_history_menu(interaction)
                        else:
                            await interaction.response.send_message(
                                "❌ Alliance History module not found.",
                                ephemeral=True
                            )
                    except Exception as e:
                        print(f"Alliance history error: {e}")
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                "An error occurred while loading Alliance History.",
                                ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                "An error occurred while loading Alliance History.",
                                ephemeral=True
                            )

                elif custom_id == "other_features":
                    try:
                        other_features_cog = interaction.client.get_cog("OtherFeatures")
                        if other_features_cog:
                            await other_features_cog.show_other_features_menu(interaction)
                        else:
                            await interaction.response.send_message(
                                "❌ Other Features module not found.",
                                ephemeral=True
                            )
                    except Exception as e:
                        if not any(error_code in str(e) for error_code in ["10062", "40060"]):
                            print(f"Other features error: {e}")
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                "An error occurred while loading Other Features menu.",
                                ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                "An error occurred while loading Other Features menu.",
                                ephemeral=True
                            )

            except Exception as e:
                if not any(error_code in str(e) for error_code in ["10062", "40060"]):
                    print(f"Error processing interaction with custom_id '{custom_id}': {e}")
                await interaction.response.send_message(
                    "An error occurred while processing your request. Please try again.",
                    ephemeral=True
                )

    async def add_alliance(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("Please perform this action in a Discord channel.", ephemeral=True)
            return

        modal = AllianceModal(title="Add Alliance")
        await interaction.response.send_modal(modal)
        await modal.wait()

        try:
            alliance_name = modal.name.value.strip()
            interval = int(modal.interval.value.strip())

            embed = discord.Embed(
                title="Channel Selection",
                description=(
                    "**Instructions:**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "Please select a channel for the alliance\n\n"
                    "**Page:** 1/1\n"
                    f"**Total Channels:** {len(interaction.guild.text_channels)}"
                ),
                color=discord.Color.blue()
            )

            async def channel_select_callback(select_interaction: discord.Interaction):
                try:
                    self.c.execute("SELECT alliance_id FROM alliance_list WHERE name = ?", (alliance_name,))
                    existing_alliance = self.c.fetchone()
                    
                    if existing_alliance:
                        error_embed = discord.Embed(
                            title="Error",
                            description="An alliance with this name already exists.",
                            color=discord.Color.red()
                        )
                        await select_interaction.response.edit_message(embed=error_embed, view=None)
                        return

                    channel_id = int(select_interaction.data["values"][0])

                    self.c.execute("INSERT INTO alliance_list (name, discord_server_id) VALUES (?, ?)", 
                                 (alliance_name, interaction.guild.id))
                    alliance_id = self.c.lastrowid
                    self.c.execute("INSERT INTO alliancesettings (alliance_id, channel_id, interval) VALUES (?, ?, ?)", 
                                 (alliance_id, channel_id, interval))
                    self.conn.commit()
                    if mongo_enabled():
                        try:
                            AlliancesAdapter.upsert(alliance_id, alliance_name, interaction.guild.id)
                            AllianceSettingsAdapter.upsert(alliance_id, channel_id, interval, giftcodecontrol=1)
                        except Exception:
                            pass

                    self.c_giftcode.execute("""
                        INSERT INTO giftcodecontrol (alliance_id, status) 
                        VALUES (?, 1)
                    """, (alliance_id,))
                    self.conn_giftcode.commit()

                    result_embed = discord.Embed(
                        title="✅ Alliance Successfully Created",
                        description="The alliance has been created with the following details:",
                        color=discord.Color.green()
                    )
                    
                    info_section = (
                        f"**🛡️ Alliance Name**\n{alliance_name}\n\n"
                        f"**🔢 Alliance ID**\n{alliance_id}\n\n"
                        f"**📢 Channel**\n<#{channel_id}>\n\n"
                        f"**⏱️ Control Interval**\n{interval} minutes"
                    )
                    result_embed.add_field(name="Alliance Details", value=info_section, inline=False)
                    
                    result_embed.set_footer(text="Alliance settings have been successfully saved")
                    result_embed.timestamp = discord.utils.utcnow()
                    
                    await select_interaction.response.edit_message(embed=result_embed, view=None)

                except Exception as e:
                    error_embed = discord.Embed(
                        title="Error",
                        description=f"Error creating alliance: {str(e)}",
                        color=discord.Color.red()
                    )
                    await select_interaction.response.edit_message(embed=error_embed, view=None)

            channels = interaction.guild.text_channels
            view = PaginatedChannelView(channels, channel_select_callback)
            await modal.interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except ValueError:
            error_embed = discord.Embed(
                title="Error",
                description="Invalid interval value. Please enter a number.",
                color=discord.Color.red()
            )
            await modal.interaction.response.send_message(embed=error_embed, ephemeral=True)
        except Exception as e:
            error_embed = discord.Embed(
                title="Error",
                description=f"Error: {str(e)}",
                color=discord.Color.red()
            )
            await modal.interaction.response.send_message(embed=error_embed, ephemeral=True)

    async def edit_alliance(self, interaction: discord.Interaction):
        self.c.execute("""
            SELECT a.alliance_id, a.name, COALESCE(s.interval, 0) as interval, COALESCE(s.channel_id, 0) as channel_id 
            FROM alliance_list a 
            LEFT JOIN alliancesettings s ON a.alliance_id = s.alliance_id
            ORDER BY a.alliance_id ASC
        """)
        alliances = self.c.fetchall()
        
        if not alliances:
            no_alliance_embed = discord.Embed(
                title="❌ No Alliances Found",
                description=(
                    "There are no alliances registered in the database.\n"
                    "Please create an alliance first using the `/alliance create` command."
                ),
                color=discord.Color.red()
            )
            no_alliance_embed.set_footer(text="Use /alliance create to add a new alliance")
            return await interaction.response.send_message(embed=no_alliance_embed, ephemeral=True)

        alliance_options = [
            discord.SelectOption(
                label=f"{name} (ID: {alliance_id})",
                value=f"{alliance_id}",
                description=f"Interval: {interval} minutes"
            ) for alliance_id, name, interval, _ in alliances
        ]
        
        items_per_page = 25
        option_pages = [alliance_options[i:i + items_per_page] for i in range(0, len(alliance_options), items_per_page)]
        total_pages = len(option_pages)

        class PaginatedAllianceView(discord.ui.View):
            def __init__(self, pages, original_callback):
                super().__init__(timeout=7200)
                self.current_page = 0
                self.pages = pages
                self.original_callback = original_callback
                self.total_pages = len(pages)
                self.update_view()

            def update_view(self):
                self.clear_items()
                
                select = discord.ui.Select(
                    placeholder=f"Select alliance ({self.current_page + 1}/{self.total_pages})",
                    options=self.pages[self.current_page]
                )
                select.callback = self.original_callback
                self.add_item(select)
                
                previous_button = discord.ui.Button(
                    label="◀️",
                    style=discord.ButtonStyle.grey,
                    custom_id="previous",
                    disabled=(self.current_page == 0)
                )
                previous_button.callback = self.previous_callback
                self.add_item(previous_button)

                next_button = discord.ui.Button(
                    label="▶️",
                    style=discord.ButtonStyle.grey,
                    custom_id="next",
                    disabled=(self.current_page == len(self.pages) - 1)
                )
                next_button.callback = self.next_callback
                self.add_item(next_button)

            async def previous_callback(self, interaction: discord.Interaction):
                self.current_page = (self.current_page - 1) % len(self.pages)
                self.update_view()
                
                embed = interaction.message.embeds[0]
                embed.description = (
                    "**Instructions:**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "1️⃣ Select an alliance from the dropdown menu\n"
                    "2️⃣ Use ◀️ ▶️ buttons to navigate between pages\n\n"
                    f"**Current Page:** {self.current_page + 1}/{self.total_pages}\n"
                    f"**Total Alliances:** {sum(len(page) for page in self.pages)}\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                )
                await interaction.response.edit_message(embed=embed, view=self)

            async def next_callback(self, interaction: discord.Interaction):
                self.current_page = (self.current_page + 1) % len(self.pages)
                self.update_view()
                
                embed = interaction.message.embeds[0]
                embed.description = (
                    "**Instructions:**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "1️⃣ Select an alliance from the dropdown menu\n"
                    "2️⃣ Use ◀️ ▶️ buttons to navigate between pages\n\n"
                    f"**Current Page:** {self.current_page + 1}/{self.total_pages}\n"
                    f"**Total Alliances:** {sum(len(page) for page in self.pages)}\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                )
                await interaction.response.edit_message(embed=embed, view=self)

        async def select_callback(select_interaction: discord.Interaction):
            try:
                alliance_id = int(select_interaction.data["values"][0])
                alliance_data = next(a for a in alliances if a[0] == alliance_id)
                
                self.c.execute("""
                    SELECT interval, channel_id 
                    FROM alliancesettings 
                    WHERE alliance_id = ?
                """, (alliance_id,))
                settings_data = self.c.fetchone()
                
                modal = AllianceModal(
                    title="Edit Alliance",
                    default_name=alliance_data[1],
                    default_interval=str(settings_data[0] if settings_data else 0)
                )
                await select_interaction.response.send_modal(modal)
                await modal.wait()

                try:
                    alliance_name = modal.name.value.strip()
                    interval = int(modal.interval.value.strip())

                    embed = discord.Embed(
                        title="🔄 Channel Selection",
                        description=(
                            "**Current Channel Information**\n"
                            "━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"📢 Current channel: {f'<#{settings_data[1]}>' if settings_data else 'Not set'}\n"
                            "**Page:** 1/1\n"
                            f"**Total Channels:** {len(interaction.guild.text_channels)}\n"
                            "━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=discord.Color.blue()
                    )

                    async def channel_select_callback(channel_interaction: discord.Interaction):
                        try:
                            channel_id = int(channel_interaction.data["values"][0])

                            self.c.execute("UPDATE alliance_list SET name = ? WHERE alliance_id = ?", 
                                          (alliance_name, alliance_id))

                            if settings_data:
                                self.c.execute("""
                                    UPDATE alliancesettings 
                                    SET channel_id = ?, interval = ? 
                                    WHERE alliance_id = ?
                                """, (channel_id, interval, alliance_id))
                            else:
                                self.c.execute("""
                                    INSERT INTO alliancesettings (alliance_id, channel_id, interval)
                                    VALUES (?, ?, ?)
                                """, (alliance_id, channel_id, interval))
                            
                            self.conn.commit()
                            if mongo_enabled():
                                try:
                                    AlliancesAdapter.upsert(alliance_id, alliance_name, interaction.guild.id)
                                    AllianceSettingsAdapter.upsert(alliance_id, channel_id, interval)
                                except Exception:
                                    pass

                            result_embed = discord.Embed(
                                title="✅ Alliance Successfully Updated",
                                description="The alliance details have been updated as follows:",
                                color=discord.Color.green()
                            )
                            
                            info_section = (
                                f"**🛡️ Alliance Name**\n{alliance_name}\n\n"
                                f"**🔢 Alliance ID**\n{alliance_id}\n\n"
                                f"**📢 Channel**\n<#{channel_id}>\n\n"
                                f"**⏱️ Control Interval**\n{interval} minutes"
                            )
                            result_embed.add_field(name="Alliance Details", value=info_section, inline=False)
                            
                            result_embed.set_footer(text="Alliance settings have been successfully saved")
                            result_embed.timestamp = discord.utils.utcnow()
                            
                            await channel_interaction.response.edit_message(embed=result_embed, view=None)

                        except Exception as e:
                            error_embed = discord.Embed(
                                title="❌ Error",
                                description=f"An error occurred while updating the alliance: {str(e)}",
                                color=discord.Color.red()
                            )
                            await channel_interaction.response.edit_message(embed=error_embed, view=None)

                    channels = interaction.guild.text_channels
                    view = PaginatedChannelView(channels, channel_select_callback)
                    await modal.interaction.response.send_message(embed=embed, view=view, ephemeral=True)

                except ValueError:
                    error_embed = discord.Embed(
                        title="Error",
                        description="Invalid interval value. Please enter a number.",
                        color=discord.Color.red()
                    )
                    await modal.interaction.response.send_message(embed=error_embed, ephemeral=True)
                except Exception as e:
                    error_embed = discord.Embed(
                        title="Error",
                        description=f"Error: {str(e)}",
                        color=discord.Color.red()
                    )
                    await modal.interaction.response.send_message(embed=error_embed, ephemeral=True)

            except Exception as e:
                error_embed = discord.Embed(
                    title="❌ Error",
                    description=f"An error occurred: {str(e)}",
                    color=discord.Color.red()
                )
                if not select_interaction.response.is_done():
                    await select_interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    await select_interaction.followup.send(embed=error_embed, ephemeral=True)

        view = PaginatedAllianceView(option_pages, select_callback)
        embed = discord.Embed(
            title="🛡️ Alliance Edit Menu",
            description=(
                "**Instructions:**\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "1️⃣ Select an alliance from the dropdown menu\n"
                "2️⃣ Use ◀️ ▶️ buttons to navigate between pages\n\n"
                f"**Current Page:** {1}/{total_pages}\n"
                f"**Total Alliances:** {len(alliances)}\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Use the dropdown menu below to select an alliance")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def delete_alliance(self, interaction: discord.Interaction):
        try:
            self.c.execute("SELECT alliance_id, name FROM alliance_list ORDER BY name")
            alliances = self.c.fetchall()
            
            if not alliances:
                no_alliance_embed = discord.Embed(
                    title="❌ No Alliances Found",
                    description="There are no alliances to delete.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=no_alliance_embed, ephemeral=True)
                return

            alliance_members = {}
            for alliance_id, _ in alliances:
                self.c_users.execute("SELECT COUNT(*) FROM users WHERE alliance = ?", (alliance_id,))
                member_count = self.c_users.fetchone()[0]
                alliance_members[alliance_id] = member_count

            items_per_page = 25
            all_options = [
                discord.SelectOption(
                    label=f"{name[:40]} (ID: {alliance_id})",
                    value=f"{alliance_id}",
                    description=f"👥 Members: {alliance_members[alliance_id]} | Click to delete",
                    emoji="🗑️"
                ) for alliance_id, name in alliances
            ]
            
            option_pages = [all_options[i:i + items_per_page] for i in range(0, len(all_options), items_per_page)]
            
            embed = discord.Embed(
                title="🗑️ Delete Alliance",
                description=(
                    "**⚠️ Warning: This action cannot be undone!**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "1️⃣ Select an alliance from the dropdown menu\n"
                    "2️⃣ Use ◀️ ▶️ buttons to navigate between pages\n\n"
                    f"**Current Page:** 1/{len(option_pages)}\n"
                    f"**Total Alliances:** {len(alliances)}\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=discord.Color.red()
            )
            embed.set_footer(text="⚠️ Warning: Deleting an alliance will remove all its data!")
            embed.timestamp = discord.utils.utcnow()

            view = PaginatedDeleteView(option_pages, self.alliance_delete_callback)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"Error in delete_alliance: {e}")
            error_embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while loading the delete menu.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    async def alliance_delete_callback(self, interaction: discord.Interaction):
        try:
            alliance_id = int(interaction.data["values"][0])
            
            self.c.execute("SELECT name FROM alliance_list WHERE alliance_id = ?", (alliance_id,))
            alliance_data = self.c.fetchone()
            
            if not alliance_data:
                await interaction.response.send_message("Alliance not found.", ephemeral=True)
                return
            
            alliance_name = alliance_data[0]

            self.c.execute("SELECT COUNT(*) FROM alliancesettings WHERE alliance_id = ?", (alliance_id,))
            settings_count = self.c.fetchone()[0]

            self.c_users.execute("SELECT COUNT(*) FROM users WHERE alliance = ?", (alliance_id,))
            users_count = self.c_users.fetchone()[0]

            self.c_settings.execute("SELECT COUNT(*) FROM adminserver WHERE alliances_id = ?", (alliance_id,))
            admin_server_count = self.c_settings.fetchone()[0]

            self.c_giftcode.execute("SELECT COUNT(*) FROM giftcode_channel WHERE alliance_id = ?", (alliance_id,))
            gift_channels_count = self.c_giftcode.fetchone()[0]

            self.c_giftcode.execute("SELECT COUNT(*) FROM giftcodecontrol WHERE alliance_id = ?", (alliance_id,))
            gift_code_control_count = self.c_giftcode.fetchone()[0]

            confirm_embed = discord.Embed(
                title="⚠️ Confirm Alliance Deletion",
                description=(
                    f"Are you sure you want to delete this alliance?\n\n"
                    f"**Alliance Details:**\n"
                    f"🛡️ **Name:** {alliance_name}\n"
                    f"🔢 **ID:** {alliance_id}\n"
                    f"👥 **Members:** {users_count}\n\n"
                    f"**Data to be Deleted:**\n"
                    f"⚙️ Alliance Settings: {settings_count}\n"
                    f"👥 User Records: {users_count}\n"
                    f"🏰 Admin Server Records: {admin_server_count}\n"
                    f"📢 Gift Channels: {gift_channels_count}\n"
                    f"📊 Gift Code Controls: {gift_code_control_count}\n\n"
                    "**⚠️ WARNING: This action cannot be undone!**"
                ),
                color=discord.Color.red()
            )
            
            confirm_view = discord.ui.View(timeout=60)
            
            async def confirm_callback(button_interaction: discord.Interaction):
                try:
                    self.c.execute("DELETE FROM alliance_list WHERE alliance_id = ?", (alliance_id,))
                    alliance_count = self.c.rowcount
                    
                    self.c.execute("DELETE FROM alliancesettings WHERE alliance_id = ?", (alliance_id,))
                    admin_settings_count = self.c.rowcount
                    
                    self.conn.commit()

                    self.c_users.execute("DELETE FROM users WHERE alliance = ?", (alliance_id,))
                    users_count_deleted = self.c_users.rowcount
                    self.conn_users.commit()

                    self.c_settings.execute("DELETE FROM adminserver WHERE alliances_id = ?", (alliance_id,))
                    admin_server_count = self.c_settings.rowcount
                    self.conn_settings.commit()

                    self.c_giftcode.execute("DELETE FROM giftcode_channel WHERE alliance_id = ?", (alliance_id,))
                    gift_channels_count = self.c_giftcode.rowcount

                    self.c_giftcode.execute("DELETE FROM giftcodecontrol WHERE alliance_id = ?", (alliance_id,))
                    gift_code_control_count = self.c_giftcode.rowcount
                    
                    self.conn_giftcode.commit()
                    if mongo_enabled():
                        try:
                            AlliancesAdapter.delete(alliance_id)
                            AllianceSettingsAdapter.delete(alliance_id)
                        except Exception:
                            pass

                    cleanup_embed = discord.Embed(
                        title="✅ Alliance Successfully Deleted",
                        description=(
                            f"Alliance **{alliance_name}** has been deleted.\n\n"
                            "**Cleaned Up Data:**\n"
                            f"🛡️ Alliance Records: {alliance_count}\n"
                            f"👥 Users Removed: {users_count_deleted}\n"
                            f"⚙️ Alliance Settings: {admin_settings_count}\n"
                            f"🏰 Admin Server Records: {admin_server_count}\n"
                            f"📢 Gift Channels: {gift_channels_count}\n"
                            f"📊 Gift Code Controls: {gift_code_control_count}"
                        ),
                        color=discord.Color.green()
                    )
                    cleanup_embed.set_footer(text="All related data has been successfully removed")
                    cleanup_embed.timestamp = discord.utils.utcnow()
                    
                    await button_interaction.response.edit_message(embed=cleanup_embed, view=None)
                    
                except Exception as e:
                    error_embed = discord.Embed(
                        title="❌ Error",
                        description=f"An error occurred while deleting the alliance: {str(e)}",
                        color=discord.Color.red()
                    )
                    await button_interaction.response.edit_message(embed=error_embed, view=None)

            async def cancel_callback(button_interaction: discord.Interaction):
                cancel_embed = discord.Embed(
                    title="❌ Deletion Cancelled",
                    description="Alliance deletion has been cancelled.",
                    color=discord.Color.grey()
                )
                await button_interaction.response.edit_message(embed=cancel_embed, view=None)

            confirm_button = discord.ui.Button(label="Confirm", style=discord.ButtonStyle.danger)
            cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.grey)
            confirm_button.callback = confirm_callback
            cancel_button.callback = cancel_callback
            confirm_view.add_item(confirm_button)
            confirm_view.add_item(cancel_button)

            await interaction.response.edit_message(embed=confirm_embed, view=confirm_view)

        except Exception as e:
            print(f"Error in alliance_delete_callback: {e}")
            error_embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while processing the deletion.",
                color=discord.Color.red()
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=True)

    async def handle_button_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        
        if custom_id == "main_menu":
            embed = discord.Embed(
                title="⚙️ Settings Menu",
                description=(
                    "Please select a category:\n\n"
                    "**Menu Categories**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🏰 **Alliance Operations**\n"
                    "└ Manage alliances and settings\n\n"
                    "👥 **Alliance Member Operations**\n"
                    "└ Add, remove, and view members\n\n"
                    "🤖 **Bot Operations**\n"
                    "└ Configure bot settings\n\n"
                    "🎁 **Gift Code Operations**\n"
                    "└ Manage gift codes and rewards\n\n"
                    "📜 **Alliance History**\n"
                    "└ View alliance changes and history\n\n"
                    "🆘 **Support Operations**\n"
                    "└ Access support features\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=discord.Color.blue()
            )
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="Alliance Operations",
                emoji="🏰",
                style=discord.ButtonStyle.primary,
                custom_id="alliance_operations",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label="Member Operations",
                emoji="👥",
                style=discord.ButtonStyle.primary,
                custom_id="member_operations",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label="Bot Operations",
                emoji="🤖",
                style=discord.ButtonStyle.primary,
                custom_id="bot_operations",
                row=1
            ))
            view.add_item(discord.ui.Button(
                label="Gift Operations",
                emoji="🎁",
                style=discord.ButtonStyle.primary,
                custom_id="gift_code_operations",
                row=1
            ))
            view.add_item(discord.ui.Button(
                label="Alliance History",
                emoji="📜",
                style=discord.ButtonStyle.primary,
                custom_id="alliance_history",
                row=2
            ))
            view.add_item(discord.ui.Button(
                label="Support Operations",
                emoji="🆘",
                style=discord.ButtonStyle.primary,
                custom_id="support_operations",
                row=2
            ))
            view.add_item(discord.ui.Button(
                label="Other Features",
                emoji="🔧",
                style=discord.ButtonStyle.primary,
                custom_id="other_features",
                row=3
            ))


            await interaction.response.edit_message(embed=embed, view=view)

        elif custom_id == "other_features":
            try:
                other_features_cog = interaction.client.get_cog("OtherFeatures")
                if other_features_cog:
                    await other_features_cog.show_other_features_menu(interaction)
                else:
                    await interaction.response.send_message(
                        "❌ Other Features module not found.",
                        ephemeral=True
                    )
            except Exception as e:
                if not any(error_code in str(e) for error_code in ["10062", "40060"]):
                    print(f"Other features error: {e}")
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "An error occurred while loading Other Features menu.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "An error occurred while loading Other Features menu.",
                        ephemeral=True
                    )

    async def show_main_menu(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="⚙️ Settings Menu",
                description=(
                    "Please select a category:\n\n"
                    "**Menu Categories**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🏰 **Alliance Operations**\n"
                    "└ Manage alliances and settings\n\n"
                    "👥 **Alliance Member Operations**\n"
                    "└ Add, remove, and view members\n\n"
                    "🤖 **Bot Operations**\n"
                    "└ Configure bot settings\n\n"
                    "🎁 **Gift Code Operations**\n"
                    "└ Manage gift codes and rewards\n\n"
                    "📜 **Alliance History**\n"
                    "└ View alliance changes and history\n\n"
                    "🆘 **Support Operations**\n"
                    "└ Access support features\n\n"
                    "🔧 **Other Features**\n"
                    "└ Access other features\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=discord.Color.blue()
            )
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="Alliance Operations",
                emoji="🏰",
                style=discord.ButtonStyle.primary,
                custom_id="alliance_operations",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label="Member Operations",
                emoji="👥",
                style=discord.ButtonStyle.primary,
                custom_id="member_operations",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label="Bot Operations",
                emoji="🤖",
                style=discord.ButtonStyle.primary,
                custom_id="bot_operations",
                row=1
            ))
            view.add_item(discord.ui.Button(
                label="Gift Operations",
                emoji="🎁",
                style=discord.ButtonStyle.primary,
                custom_id="gift_code_operations",
                row=1
            ))
            view.add_item(discord.ui.Button(
                label="Alliance History",
                emoji="📜",
                style=discord.ButtonStyle.primary,
                custom_id="alliance_history",
                row=2
            ))
            view.add_item(discord.ui.Button(
                label="Support Operations",
                emoji="🆘",
                style=discord.ButtonStyle.primary,
                custom_id="support_operations",
                row=2
            ))
            view.add_item(discord.ui.Button(
                label="Other Features",
                emoji="🔧",
                style=discord.ButtonStyle.primary,
                custom_id="other_features",
                row=3
            ))

            try:
                await interaction.response.edit_message(embed=embed, view=view)
            except discord.InteractionResponded:
                pass
                
        except Exception as e:
            pass

    @discord.ui.button(label="Bot Operations", emoji="🤖", style=discord.ButtonStyle.primary, custom_id="bot_operations", row=1)
    async def bot_operations_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            bot_ops_cog = interaction.client.get_cog("BotOperations")
            if bot_ops_cog:
                await bot_ops_cog.show_bot_operations_menu(interaction)
            else:
                await interaction.response.send_message(
                    "❌ Bot Operations module not found.",
                    ephemeral=True
                )
        except Exception as e:
            print(f"Bot operations button error: {e}")
            await interaction.response.send_message(
                "❌ An error occurred. Please try again.",
                ephemeral=True
            )

    # =========================================================================
    # ALLIANCE MONITORING METHODS
    # =========================================================================

    def log_message(self, message: str):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)

    def _set_embed_footer(self, embed: discord.Embed):
        """Set the standard footer for alliance monitoring embeds"""
        embed.set_footer(
            text="Whiteout Survival || by Gιɳα 🚀",
            icon_url="https://cdn.discordapp.com/attachments/1435569370389807144/1436745053442805830/unnamed_5.png?ex=6921335a&is=691fe1da&hm=9b8fa5ee98abc7630652de0cca2bd0521be394317e450a9bfdc5c48d0482dffe"
        )
    
    def _initialize_monitoring_tables(self):
        """Create necessary database tables if they don't exist"""
        try:
            with get_db_connection('settings.sqlite') as conn:
                cursor = conn.cursor()
                
                # Alliance monitoring configuration table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS alliance_monitoring (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        alliance_id INTEGER NOT NULL,
                        channel_id INTEGER NOT NULL,
                        enabled INTEGER DEFAULT 1,
                        check_interval INTEGER DEFAULT 300,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(guild_id, alliance_id)
                    )
                """)
                
                # Member history table for change detection
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS member_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fid TEXT NOT NULL,
                        alliance_id INTEGER NOT NULL,
                        nickname TEXT NOT NULL,
                        furnace_lv INTEGER NOT NULL,
                        last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(fid, alliance_id)
                    )
                """)
                
                conn.commit()
                self.log_message("Database tables initialized successfully")
                
                # Check if avatar_image column exists in member_history
                try:
                    cursor.execute("SELECT avatar_image FROM member_history LIMIT 1")
                except Exception:
                    try:
                        cursor.execute("ALTER TABLE member_history ADD COLUMN avatar_image TEXT")
                        conn.commit()
                        self.log_message("Added avatar_image column to member_history")
                    except Exception as e:
                        self.log_message(f"Error adding avatar_image column: {e}")
                        
        except Exception as e:
            self.log_message(f"Error initializing database: {e}")
    
    def get_fl_emoji(self, fl_level: int) -> str:
        """Get emoji for furnace level"""
        for level_range, emoji in self.fl_emojis.items():
            if fl_level in level_range:
                return emoji
        return "🔥"
    
    def _get_monitoring_members(self, alliance_id: int) -> list:
        """Get all members of an alliance from database"""
        members = []
        try:
            if mongo_enabled() and AllianceMembersAdapter is not None:
                docs = AllianceMembersAdapter.get_all_members() or []
                res = []
                for d in docs:
                    try:
                        if int(d.get('alliance') or d.get('alliance_id') or 0) != int(alliance_id):
                            continue
                        fid = str(d.get('fid') or d.get('id') or d.get('_id'))
                        nickname = d.get('nickname') or d.get('name') or ''
                        furnace_lv = int(d.get('furnace_lv') or d.get('furnaceLevel') or d.get('furnace', 0) or 0)
                        res.append((fid, nickname, furnace_lv))
                    except Exception:
                        continue
                if res:
                    return res
        except Exception:
            pass

        # SQLite fallback
        try:
            with get_db_connection('users.sqlite') as users_db:
                cursor = users_db.cursor()
                cursor.execute("SELECT fid, nickname, furnace_lv FROM users WHERE alliance = ?", (alliance_id,))
                return cursor.fetchall()
        except Exception:
            return []
    
    async def _get_monitored_alliances(self) -> List[Dict]:
        """Get all alliances that are being monitored"""
        try:
            with get_db_connection('settings.sqlite') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, guild_id, alliance_id, channel_id, enabled, check_interval
                    FROM alliance_monitoring
                    WHERE enabled = 1
                """)
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'id': row[0],
                        'guild_id': row[1],
                        'alliance_id': row[2],
                        'channel_id': row[3],
                        'enabled': row[4],
                        'check_interval': row[5]
                    })
                return results
        except Exception as e:
            self.log_message(f"Error getting monitored alliances: {e}")
            return []
    
    async def _check_alliance_changes(self, alliance_id: int, channel_id: int, guild_id: int):
        """Check for changes in an alliance and post notifications"""
        try:
            # Get alliance name
            alliance_name = "Unknown Alliance"
            try:
                with get_db_connection('alliance.sqlite') as alliance_db:
                    cursor = alliance_db.cursor()
                    cursor.execute("SELECT name FROM alliance_list WHERE alliance_id = ?", (alliance_id,))
                    result = cursor.fetchone()
                    if result:
                        alliance_name = result[0]
            except Exception as e:
                self.log_message(f"Error getting alliance name: {e}")
            
            # Get current members from database
            current_members = self._get_monitoring_members(alliance_id)
            
            if not current_members:
                self.log_message(f"No members found for alliance {alliance_id}")
                return
            
            # Get channel
            channel = self.bot.get_channel(channel_id)
            if not channel:
                self.log_message(f"Channel {channel_id} not found")
                return
            
            # Check each member for changes
            changes_detected = []
            
            for fid, current_nickname, current_furnace_lv in current_members:
                # Fetch latest data from API
                api_result = await self.login_handler.fetch_player_data(str(fid))
                
                if api_result['status'] == 'success':
                    api_data = api_result['data']
                    api_nickname = api_data.get('nickname', current_nickname)
                    api_furnace_lv = api_data.get('stove_lv', current_furnace_lv)
                    
                    # Get historical data
                    with get_db_connection('settings.sqlite') as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT nickname, furnace_lv, avatar_image
                            FROM member_history 
                            WHERE fid = ? AND alliance_id = ?
                        """, (str(fid), alliance_id))
                        
                        history = cursor.fetchone()
                        
                        if history:
                            old_nickname = history[0]
                            old_furnace_lv = history[1]
                            
                            # Check for name change
                            if api_nickname != old_nickname:
                                changes_detected.append({
                                    'type': 'name_change',
                                    'fid': fid,
                                    'old_value': old_nickname,
                                    'new_value': api_nickname,
                                    'furnace_lv': api_furnace_lv,
                                    'alliance_name': alliance_name
                                })
                            
                            # Check for avatar change
                            api_avatar = api_data.get('avatar_image', '')
                            old_avatar = history[2] if len(history) > 2 else ''
                            
                            if api_avatar and old_avatar and api_avatar != old_avatar:
                                changes_detected.append({
                                    'type': 'avatar_change',
                                    'fid': fid,
                                    'nickname': api_nickname,
                                    'old_value': old_avatar,
                                    'new_value': api_avatar,
                                    'furnace_lv': api_furnace_lv,
                                    'alliance_name': alliance_name
                                })
                            
                            # Check for furnace level change
                            if api_furnace_lv != old_furnace_lv:
                                changes_detected.append({
                                    'type': 'furnace_change',
                                    'fid': fid,
                                    'nickname': api_nickname,
                                    'old_value': old_furnace_lv,
                                    'new_value': api_furnace_lv,
                                    'alliance_name': alliance_name
                                })
                        
                        # Update or insert history
                        api_avatar = api_data.get('avatar_image', '')
                        cursor.execute("""
                            INSERT OR REPLACE INTO member_history 
                            (fid, alliance_id, nickname, furnace_lv, avatar_image, last_checked)
                            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (str(fid), alliance_id, api_nickname, api_furnace_lv, api_avatar))
                        
                        conn.commit()
                
                # Add delay to respect rate limits
                await asyncio.sleep(self.login_handler.request_delay)
            
            # Post change notifications
            for change in changes_detected:
                embed = self._create_change_embed(change)
                await channel.send(embed=embed)
                self.log_message(f"Posted {change['type']} notification for FID {change['fid']}")
            
            if changes_detected:
                self.log_message(f"Detected {len(changes_detected)} changes for alliance {alliance_id}")
            
        except Exception as e:
            self.log_message(f"Error checking alliance {alliance_id}: {e}")
    
    def _create_change_embed(self, change: Dict) -> discord.Embed:
        """Create an attractive embed for a detected change"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        if change['type'] == 'name_change':
            embed = discord.Embed(
                title="👤 Name Change Detected",
                color=discord.Color.blue()
            )
            
            furnace_level_str = self.level_mapping.get(change['furnace_lv'], str(change['furnace_lv']))
            fl_emoji = self.get_fl_emoji(change['furnace_lv'])
            
            embed.add_field(name="🆔 Player ID", value=f"`{change['fid']}`", inline=False)
            embed.add_field(name="📝 Old Name", value=f"~~`{change['old_value']}`~~", inline=True)
            embed.add_field(name="✨ New Name", value=f"**`{change['new_value']}`**", inline=True)
            embed.add_field(name="⚔️ Furnace Level", value=f"`{fl_emoji} {furnace_level_str}`", inline=False)
            embed.add_field(name="🏰 Alliance", value=f"`{change['alliance_name']}`", inline=True)
            embed.add_field(name="🕐 Time", value=f"`{timestamp}`", inline=True)
            
        elif change['type'] == 'avatar_change':
            embed = discord.Embed(
                title="🖼️ Avatar Change Detected",
                color=discord.Color.purple()
            )
            
            furnace_level_str = self.level_mapping.get(change['furnace_lv'], str(change['furnace_lv']))
            fl_emoji = self.get_fl_emoji(change['furnace_lv'])
            
            embed.add_field(name="🆔 Player ID", value=f"`{change['fid']}`", inline=False)
            embed.add_field(name="👤 Player", value=f"`{change['nickname']}`", inline=False)
            embed.add_field(name="⚔️ Furnace Level", value=f"`{fl_emoji} {furnace_level_str}`", inline=False)
            embed.add_field(name="🏰 Alliance", value=f"`{change['alliance_name']}`", inline=True)
            embed.add_field(name="🕐 Time", value=f"`{timestamp}`", inline=True)
            embed.add_field(name="Old Profile ↗️", value="*(See Thumbnail)*", inline=True)
            
            embed.add_field(name="New Profile ⬇️", value="*(See Image Below)*", inline=False)
            
            # Set old avatar as thumbnail and new avatar as image
            if change['old_value']:
                embed.set_thumbnail(url=change['old_value'])
            
            if change['new_value']:
                embed.set_image(url=change['new_value'])
            
        elif change['type'] == 'furnace_change':
            # Determine if it's an upgrade or downgrade
            is_upgrade = change['new_value'] > change['old_value']
            title = "🔥 Furnace Level Up!" if is_upgrade else "📉 Furnace Level Change"
            color = discord.Color.green() if is_upgrade else discord.Color.orange()
            
            embed = discord.Embed(
                title=title,
                color=color
            )
            
            old_level_str = self.level_mapping.get(change['old_value'], str(change['old_value']))
            new_level_str = self.level_mapping.get(change['new_value'], str(change['new_value']))
            old_emoji = self.get_fl_emoji(change['old_value'])
            new_emoji = self.get_fl_emoji(change['new_value'])
            
            embed.add_field(name="🆔 Player ID", value=f"`{change['fid']}`", inline=False)
            embed.add_field(name="👤 Player", value=f"`{change['nickname']}`", inline=False)
            embed.add_field(name="📊 Old Level", value=f"`{old_emoji} {old_level_str}`", inline=True)
            embed.add_field(name="🎉 New Level", value=f"`{new_emoji} {new_level_str}`", inline=True)
            embed.add_field(name="🏰 Alliance", value=f"`{change['alliance_name']}`", inline=True)
            embed.add_field(name="🕐 Time", value=f"`{timestamp}`", inline=True)
        
        self._set_embed_footer(embed)
        return embed
    
    @tasks.loop(minutes=5)
    async def monitor_alliances(self):
        """Background task that monitors alliances for changes"""
        try:
            self.log_message("Starting alliance monitoring cycle")
            
            monitored = await self._get_monitored_alliances()
            
            if not monitored:
                self.log_message("No alliances being monitored")
                return
            
            self.log_message(f"Monitoring {len(monitored)} alliance(s)")
            
            for config in monitored:
                await self._check_alliance_changes(
                    config['alliance_id'],
                    config['channel_id'],
                    config['guild_id']
                )
                
                # Add delay between alliances
                await asyncio.sleep(5)
            
            self.log_message("Alliance monitoring cycle completed")
            
        except Exception as e:
            self.log_message(f"Error in monitoring task: {e}")
    
    @monitor_alliances.before_loop
    async def before_monitor_alliances(self):
        """Wait for bot to be ready before starting monitoring"""
        await self.bot.wait_until_ready()
        self.log_message("Alliance monitoring task ready")
    
    @app_commands.command(name="setalliancelogchannel", description="Set the channel for alliance change logs")
    @app_commands.describe(channel="The channel where alliance changes will be logged")
    async def set_alliance_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the log channel for alliance monitoring"""
        try:
            # Check admin permissions
            admin_info = self._get_admin(interaction.user.id)
            if not admin_info:
                await interaction.response.send_message(
                    "❌ You don't have permission to use this command.",
                    ephemeral=True
                )
                return
            
            # Store the channel preference (will be linked to alliance in selectalliance command)
            await interaction.response.send_message(
                f"✅ Alliance log channel set to {channel.mention}\n\n"
                f"Now use `/selectalliance` to choose which alliance to monitor in this channel.",
                ephemeral=True
            )
            
            # Store in a temporary attribute for the next selectalliance call
            if not hasattr(self, 'pending_channels'):
                self.pending_channels = {}
            self.pending_channels[interaction.user.id] = channel.id
            
        except Exception as e:
            self.log_message(f"Error in set_alliance_log_channel: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while setting the log channel.",
                ephemeral=True
            )
    
    @app_commands.command(name="selectalliance", description="Select an alliance to monitor for changes")
    async def select_alliance(self, interaction: discord.Interaction):
        """Select which alliance to monitor"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Check admin permissions
            admin_info = self._get_admin(interaction.user.id)
            if not admin_info:
                await interaction.followup.send(
                    "❌ You don't have permission to use this command.",
                    ephemeral=True
                )
                return
            
            # Check if user has set a channel first
            if not hasattr(self, 'pending_channels') or interaction.user.id not in self.pending_channels:
                await interaction.followup.send(
                    "❌ Please use `/setalliancelogchannel` first to set the log channel.",
                    ephemeral=True
                )
                return
            
            channel_id = self.pending_channels[interaction.user.id]
            
            # Get available alliances
            try:
                with get_db_connection('alliance.sqlite') as alliance_db:
                    cursor = alliance_db.cursor()
                    cursor.execute("SELECT alliance_id, name FROM alliance_list ORDER BY name")
                    alliances = cursor.fetchall()
            except Exception as e:
                self.log_message(f"Error getting alliances: {e}")
                await interaction.followup.send(
                    "❌ Error retrieving alliance list.",
                    ephemeral=True
                )
                return
            
            if not alliances:
                await interaction.followup.send(
                    "❌ No alliances found in the database.",
                    ephemeral=True
                )
                return
            
            # Create selection embed
            embed = discord.Embed(
                title="🏰 Select Alliance to Monitor",
                description=(
                    "Choose which alliance you want to monitor for member changes.\n\n"
                    "**Monitored Changes:**\n"
                    "• 👤 Name changes\n"
                    "• 🔥 Furnace level changes\n\n"
                    f"**Log Channel:** <#{channel_id}>"
                ),
                color=discord.Color.blue()
            )
            
            # Create select menu
            options = []
            for alliance_id, name in alliances[:25]:  # Discord limit of 25 options
                options.append(
                    discord.SelectOption(
                        label=name[:100],
                        value=str(alliance_id),
                        description=f"ID: {alliance_id}",
                        emoji="🏰"
                    )
                )
            
            select = discord.ui.Select(
                placeholder="🏰 Choose an alliance...",
                options=options
            )
            
            async def select_callback(select_interaction: discord.Interaction):
                alliance_id = int(select.values[0])
                
                # Get alliance name
                alliance_name = "Unknown"
                for aid, name in alliances:
                    if aid == alliance_id:
                        alliance_name = name
                        break
                
                # Save monitoring configuration
                try:
                    with get_db_connection('settings.sqlite') as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT OR REPLACE INTO alliance_monitoring 
                            (guild_id, alliance_id, channel_id, enabled, updated_at)
                            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                        """, (interaction.guild_id, alliance_id, channel_id))
                        conn.commit()
                    
                    # Initialize member history for this alliance
                    members = self._get_monitoring_members(alliance_id)
                    if members:
                        with get_db_connection('settings.sqlite') as conn:
                            cursor = conn.cursor()
                            for fid, nickname, furnace_lv in members:
                                cursor.execute("""
                                    INSERT OR REPLACE INTO member_history 
                                    (fid, alliance_id, nickname, furnace_lv, last_checked)
                                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                                """, (str(fid), alliance_id, nickname, furnace_lv))
                            conn.commit()
                    
                    # Clean up pending channel
                    if hasattr(self, 'pending_channels') and interaction.user.id in self.pending_channels:
                        del self.pending_channels[interaction.user.id]
                    
                    success_embed = discord.Embed(
                        title="✅ Alliance Monitoring Enabled",
                        description=(
                            f"**Alliance:** {alliance_name}\n"
                            f"**Alliance ID:** {alliance_id}\n"
                            f"**Log Channel:** <#{channel_id}>\n"
                            f"**Members Tracked:** {len(members)}\n\n"
                            f"The system will check for changes every 5 minutes.\n"
                            f"You will be notified of any name or furnace level changes."
                        ),
                        color=discord.Color.green()
                    )
                    
                    self._set_embed_footer(success_embed)
                    
                    await select_interaction.response.edit_message(
                        embed=success_embed,
                        view=None
                    )
                    
                    self.log_message(f"Monitoring enabled for alliance {alliance_id} ({alliance_name}) in channel {channel_id}")
                    
                except Exception as e:
                    self.log_message(f"Error saving monitoring config: {e}")
                    await select_interaction.response.edit_message(
                        content="❌ Error saving monitoring configuration.",
                        embed=None,
                        view=None
                    )
            
            select.callback = select_callback
            view = discord.ui.View()
            view.add_item(select)
            
            await interaction.followup.send(
                embed=embed,
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            self.log_message(f"Error in select_alliance: {e}")
            await interaction.followup.send(
                "❌ An error occurred while selecting the alliance.",
                ephemeral=True
            )
    
    @app_commands.command(name="alliancemonitoringstatus", description="View current alliance monitoring status")
    async def monitoring_status(self, interaction: discord.Interaction):
        """View current monitoring configuration"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Get monitoring configurations for this guild
            with get_db_connection('settings.sqlite') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT alliance_id, channel_id, enabled, created_at, updated_at
                    FROM alliance_monitoring
                    WHERE guild_id = ?
                    ORDER BY alliance_id
                """, (interaction.guild_id,))
                
                configs = cursor.fetchall()
            
            if not configs:
                await interaction.followup.send(
                    "ℹ️ No alliances are currently being monitored in this server.",
                    ephemeral=True
                )
                return
            
            # Create status embed
            embed = discord.Embed(
                title="📊 Alliance Monitoring Status",
                description=f"Monitoring **{len(configs)}** alliance(s) in this server",
                color=discord.Color.blue()
            )
            
            for alliance_id, channel_id, enabled, created_at, updated_at in configs:
                # Get alliance name
                alliance_name = "Unknown Alliance"
                member_count = 0
                try:
                    with get_db_connection('alliance.sqlite') as alliance_db:
                        cursor = alliance_db.cursor()
                        cursor.execute("SELECT name FROM alliance_list WHERE alliance_id = ?", (alliance_id,))
                        result = cursor.fetchone()
                        if result:
                            alliance_name = result[0]
                    
                    # Get member count from history
                    with get_db_connection('settings.sqlite') as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT COUNT(*) FROM member_history WHERE alliance_id = ?
                        """, (alliance_id,))
                        member_count = cursor.fetchone()[0]
                except Exception:
                    pass
                
                status_emoji = "✅" if enabled else "❌"
                channel_mention = f"<#{channel_id}>"
                
                embed.add_field(
                    name=f"{status_emoji} {alliance_name}",
                    value=(
                        f"**ID:** {alliance_id}\n"
                        f"**Channel:** {channel_mention}\n"
                        f"**Members:** {member_count}\n"
                        f"**Status:** {'Active' if enabled else 'Disabled'}"
                    ),
                    inline=False
                )
            
            self._set_embed_footer(embed)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.log_message(f"Error in monitoring_status: {e}")
            await interaction.followup.send(
                "❌ An error occurred while retrieving monitoring status.",
                ephemeral=True
            )
    
    @app_commands.command(name="stopalliancemonitoring", description="Stop monitoring an alliance")
    async def stop_monitoring(self, interaction: discord.Interaction):
        """Stop monitoring a specific alliance"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Check admin permissions
            admin_info = self._get_admin(interaction.user.id)
            if not admin_info:
                await interaction.followup.send(
                    "❌ You don't have permission to use this command.",
                    ephemeral=True
                )
                return
            
            # Get monitored alliances for this guild
            with get_db_connection('settings.sqlite') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT alliance_id, channel_id
                    FROM alliance_monitoring
                    WHERE guild_id = ? AND enabled = 1
                """, (interaction.guild_id,))
                
                monitored = cursor.fetchall()
            
            if not monitored:
                await interaction.followup.send(
                    "ℹ️ No alliances are currently being monitored in this server.",
                    ephemeral=True
                )
                return
            
            # Get alliance names
            alliance_options = []
            for alliance_id, channel_id in monitored:
                alliance_name = "Unknown Alliance"
                try:
                    with get_db_connection('alliance.sqlite') as alliance_db:
                        cursor = alliance_db.cursor()
                        cursor.execute("SELECT name FROM alliance_list WHERE alliance_id = ?", (alliance_id,))
                        result = cursor.fetchone()
                        if result:
                            alliance_name = result[0]
                except Exception:
                    pass
                
                alliance_options.append((alliance_id, alliance_name, channel_id))
            
            # Create selection embed
            embed = discord.Embed(
                title="🛑 Stop Alliance Monitoring",
                description="Select which alliance to stop monitoring:",
                color=discord.Color.red()
            )
            
            # Create select menu
            options = []
            for alliance_id, name, channel_id in alliance_options[:25]:
                options.append(
                    discord.SelectOption(
                        label=name[:100],
                        value=str(alliance_id),
                        description=f"ID: {alliance_id} | Channel: {channel_id}",
                        emoji="🏰"
                    )
                )
            
            select = discord.ui.Select(
                placeholder="🏰 Choose an alliance to stop monitoring...",
                options=options
            )
            
            async def select_callback(select_interaction: discord.Interaction):
                alliance_id = int(select.values[0])
                
                # Get alliance name
                alliance_name = "Unknown"
                for aid, name, _ in alliance_options:
                    if aid == alliance_id:
                        alliance_name = name
                        break
                
                # Disable monitoring
                try:
                    with get_db_connection('settings.sqlite') as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE alliance_monitoring 
                            SET enabled = 0, updated_at = CURRENT_TIMESTAMP
                            WHERE guild_id = ? AND alliance_id = ?
                        """, (interaction.guild_id, alliance_id))
                        conn.commit()
                    
                    success_embed = discord.Embed(
                        title="✅ Monitoring Stopped",
                        description=(
                            f"**Alliance:** {alliance_name}\n"
                            f"**Alliance ID:** {alliance_id}\n\n"
                            f"Monitoring has been disabled for this alliance.\n"
                            f"Historical data has been preserved."
                        ),
                        color=discord.Color.green()
                    )
                    
                    self._set_embed_footer(success_embed)
                    
                    await select_interaction.response.edit_message(
                        embed=success_embed,
                        view=None
                    )
                    
                    self.log_message(f"Monitoring disabled for alliance {alliance_id} ({alliance_name})")
                    
                except Exception as e:
                    self.log_message(f"Error stopping monitoring: {e}")
                    await select_interaction.response.edit_message(
                        content="❌ Error stopping monitoring.",
                        embed=None,
                        view=None
                    )
            
            select.callback = select_callback
            view = discord.ui.View()
            view.add_item(select)
            
            await interaction.followup.send(
                embed=embed,
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            self.log_message(f"Error in stop_monitoring: {e}")
            await interaction.followup.send(
                "❌ An error occurred while stopping monitoring.",
                ephemeral=True
            )

class AllianceModal(discord.ui.Modal):
    def __init__(self, title: str, default_name: str = "", default_interval: str = "0"):
        super().__init__(title=title)
        
        self.name = discord.ui.TextInput(
            label="Alliance Name",
            placeholder="Enter alliance name",
            default=default_name,
            required=True
        )
        self.add_item(self.name)
        
        self.interval = discord.ui.TextInput(
            label="Control Interval (minutes)",
            placeholder="Enter interval (0 to disable)",
            default=default_interval,
            required=True
        )
        self.add_item(self.interval)

    async def on_submit(self, interaction: discord.Interaction):
        self.interaction = interaction

class AllianceView(discord.ui.View):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    @discord.ui.button(
        label="Main Menu",
        emoji="🏠",
        style=discord.ButtonStyle.secondary,
        custom_id="main_menu"
    )
    async def main_menu_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_main_menu(interaction)

class MemberOperationsView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    async def get_admin_alliances(self, user_id, guild_id):
        self.cog.c_settings.execute("SELECT id, is_initial FROM admin WHERE id = ?", (user_id,))
        admin = self.cog.c_settings.fetchone()
        
        if admin is None:
            return []
            
        is_initial = admin[1]
        
        if is_initial == 1:
            self.cog.c.execute("SELECT alliance_id, name FROM alliance_list ORDER BY name")
        else:
            self.cog.c.execute("""
                SELECT alliance_id, name 
                FROM alliance_list 
                WHERE discord_server_id = ? 
                ORDER BY name
            """, (guild_id,))
            
        return self.cog.c.fetchall()

    @discord.ui.button(label="Add Member", emoji="➕", style=discord.ButtonStyle.primary, custom_id="add_member")
    async def add_member_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            alliances = await self.get_admin_alliances(interaction.user.id, interaction.guild.id)
            if not alliances:
                await interaction.response.send_message("İttifak üyesi ekleme yetkiniz yok.", ephemeral=True)
                return

            options = [
                discord.SelectOption(
                    label=f"{name}",
                    value=str(alliance_id),
                    description=f"İttifak ID: {alliance_id}"
                ) for alliance_id, name in alliances
            ]

            select = discord.ui.Select(
                placeholder="Bir ittifak seçin",
                options=options,
                custom_id="alliance_select"
            )

            view = discord.ui.View()
            view.add_item(select)

            await interaction.response.send_message(
                "Üye eklemek istediğiniz ittifakı seçin:",
                view=view,
                ephemeral=True
            )

        except Exception as e:
            print(f"Error in add_member_button: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An error occurred during the process of adding a member.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "An error occurred during the process of adding a member.",
                    ephemeral=True
                )

    @discord.ui.button(label="Remove Member", emoji="➖", style=discord.ButtonStyle.danger, custom_id="remove_member")
    async def remove_member_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            alliances = await self.get_admin_alliances(interaction.user.id, interaction.guild.id)
            if not alliances:
                await interaction.response.send_message("You are not authorized to delete alliance members.", ephemeral=True)
                return

            options = [
                discord.SelectOption(
                    label=f"{name}",
                    value=str(alliance_id),
                    description=f"Alliance ID: {alliance_id}"
                ) for alliance_id, name in alliances
            ]

            select = discord.ui.Select(
                placeholder="Choose an alliance",
                options=options,
                custom_id="alliance_select_remove"
            )

            view = discord.ui.View()
            view.add_item(select)

            await interaction.response.send_message(
                "Select the alliance you want to delete members from:",
                view=view,
                ephemeral=True
            )

        except Exception as e:
            print(f"Error in remove_member_button: {e}")
            await interaction.response.send_message(
                "An error occurred during the member deletion process.",
                ephemeral=True
            )

    @discord.ui.button(label="View Members", emoji="👥", style=discord.ButtonStyle.primary, custom_id="view_members")
    async def view_members_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            alliances = await self.get_admin_alliances(interaction.user.id, interaction.guild.id)
            if not alliances:
                await interaction.response.send_message("You are not authorized to screen alliance members.", ephemeral=True)
                return

            options = [
                discord.SelectOption(
                    label=f"{name}",
                    value=str(alliance_id),
                    description=f"Alliance ID: {alliance_id}"
                ) for alliance_id, name in alliances
            ]

            select = discord.ui.Select(
                placeholder="Choose an alliance",
                options=options,
                custom_id="alliance_select_view"
            )

            view = discord.ui.View()
            view.add_item(select)

            await interaction.response.send_message(
                "Select the alliance whose members you want to view:",
                view=view,
                ephemeral=True
            )

        except Exception as e:
            print(f"Error in view_members_button: {e}")
            await interaction.response.send_message(
                "An error occurred while viewing the member list.",
                ephemeral=True
            )

    @discord.ui.button(label="Main Menu", emoji="🏠", style=discord.ButtonStyle.secondary, custom_id="main_menu")
    async def main_menu_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.cog.show_main_menu(interaction)
        except Exception as e:
            print(f"Error in main_menu_button: {e}")
            await interaction.response.send_message(
                "An error occurred during return to the main menu.",
                ephemeral=True
            )

class PaginatedDeleteView(discord.ui.View):
    def __init__(self, pages, original_callback):
        super().__init__(timeout=7200)
        self.current_page = 0
        self.pages = pages
        self.original_callback = original_callback
        self.total_pages = len(pages)
        self.update_view()

    def update_view(self):
        self.clear_items()
        
        select = discord.ui.Select(
            placeholder=f"Select alliance to delete ({self.current_page + 1}/{self.total_pages})",
            options=self.pages[self.current_page]
        )
        select.callback = self.original_callback
        self.add_item(select)
        
        previous_button = discord.ui.Button(
            label="◀️",
            style=discord.ButtonStyle.grey,
            custom_id="previous",
            disabled=(self.current_page == 0)
        )
        previous_button.callback = self.previous_callback
        self.add_item(previous_button)

        next_button = discord.ui.Button(
            label="▶️",
            style=discord.ButtonStyle.grey,
            custom_id="next",
            disabled=(self.current_page == len(self.pages) - 1)
        )
        next_button.callback = self.next_callback
        self.add_item(next_button)

    async def previous_callback(self, interaction: discord.Interaction):
        self.current_page = (self.current_page - 1) % len(self.pages)
        self.update_view()
        
        embed = discord.Embed(
            title="🗑️ Delete Alliance",
            description=(
                "**⚠️ Warning: This action cannot be undone!**\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "1️⃣ Select an alliance from the dropdown menu\n"
                "2️⃣ Use ◀️ ▶️ buttons to navigate between pages\n\n"
                f"**Current Page:** {self.current_page + 1}/{self.total_pages}\n"
                f"**Total Alliances:** {sum(len(page) for page in self.pages)}\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.red()
        )
        embed.set_footer(text="⚠️ Warning: Deleting an alliance will remove all its data!")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def next_callback(self, interaction: discord.Interaction):
        self.current_page = (self.current_page + 1) % len(self.pages)
        self.update_view()
        
        embed = discord.Embed(
            title="🗑️ Delete Alliance",
            description=(
                "**⚠️ Warning: This action cannot be undone!**\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "1️⃣ Select an alliance from the dropdown menu\n"
                "2️⃣ Use ◀️ ▶️ buttons to navigate between pages\n\n"
                f"**Current Page:** {self.current_page + 1}/{self.total_pages}\n"
                f"**Total Alliances:** {sum(len(page) for page in self.pages)}\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.red()
        )
        embed.set_footer(text="⚠️ Warning: Deleting an alliance will remove all its data!")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.edit_message(embed=embed, view=self)

class PaginatedChannelView(discord.ui.View):
    def __init__(self, channels, original_callback):
        super().__init__(timeout=7200)
        self.current_page = 0
        self.channels = channels
        self.original_callback = original_callback
        self.items_per_page = 25
        self.pages = [channels[i:i + self.items_per_page] for i in range(0, len(channels), self.items_per_page)]
        self.total_pages = len(self.pages)
        self.update_view()

    def update_view(self):
        self.clear_items()
        
        current_channels = self.pages[self.current_page]
        channel_options = [
            discord.SelectOption(
                label=f"#{channel.name}"[:100],
                value=str(channel.id),
                description=f"Channel ID: {channel.id}" if len(f"#{channel.name}") > 40 else None,
                emoji="📢"
            ) for channel in current_channels
        ]
        
        select = discord.ui.Select(
            placeholder=f"Select channel ({self.current_page + 1}/{self.total_pages})",
            options=channel_options
        )
        select.callback = self.original_callback
        self.add_item(select)
        
        if self.total_pages > 1:
            previous_button = discord.ui.Button(
                label="◀️",
                style=discord.ButtonStyle.grey,
                custom_id="previous",
                disabled=(self.current_page == 0)
            )
            previous_button.callback = self.previous_callback
            self.add_item(previous_button)

            next_button = discord.ui.Button(
                label="▶️",
                style=discord.ButtonStyle.grey,
                custom_id="next",
                disabled=(self.current_page == len(self.pages) - 1)
            )
            next_button.callback = self.next_callback
            self.add_item(next_button)

    async def previous_callback(self, interaction: discord.Interaction):
        self.current_page = (self.current_page - 1) % len(self.pages)
        self.update_view()
        
        embed = interaction.message.embeds[0]
        embed.description = (
            f"**Page:** {self.current_page + 1}/{self.total_pages}\n"
            f"**Total Channels:** {len(self.channels)}\n\n"
            "Please select a channel from the menu below."
        )
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def next_callback(self, interaction: discord.Interaction):
        self.current_page = (self.current_page + 1) % len(self.pages)
        self.update_view()
        
        embed = interaction.message.embeds[0]
        embed.description = (
            f"**Page:** {self.current_page + 1}/{self.total_pages}\n"
            f"**Total Channels:** {len(self.channels)}\n\n"
            "Please select a channel from the menu below."
        )
        
        await interaction.response.edit_message(embed=embed, view=self)

async def setup(bot):
    try:
        # Prefer using a shared connection created in main.py (attached to bot)
        conn = None
        if hasattr(bot, "_connections") and isinstance(bot._connections, dict):
            conn = bot._connections.get("conn_alliance")

        if conn is None:
            # Fallback: ensure the repository `db` folder exists and open local DB
            from pathlib import Path

            repo_root = Path(__file__).resolve().parents[1]
            db_dir = repo_root / "db"
            try:
                db_dir.mkdir(parents=True, exist_ok=True)
            except Exception as mkdir_exc:
                pass

            db_path = db_dir / "alliance.sqlite"
            conn = sqlite3.connect(str(db_path))

        cog = Alliance(bot, conn)
        await bot.add_cog(cog)
        print(f"✓ Alliance cog loaded successfully")
    except Exception as e:
        print(f"✗ Failed to setup Alliance cog: {e}")
        raise
