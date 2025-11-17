import discord
from discord.ext import commands
from discord import app_commands
import os
import sqlite3
import asyncio
import requests
from .alliance_member_operations import AllianceSelectView

# Mongo admin adapters (fallback to SQLite if not available)
try:
    from db.admin_adapters import AdminAdapter, AdminAssignmentsAdapter
except Exception:
    AdminAdapter = None
    AdminAssignmentsAdapter = None

# Import Mongo adapters module to access alliance metadata/members when available
try:
    from db import mongo_adapters as mongo_ad
except Exception:
    mongo_ad = None

class BotOperations(commands.Cog):
    def __init__(self, bot, conn):
        self.bot = bot
        self.conn = conn
        self.settings_db = sqlite3.connect('db/settings.sqlite', check_same_thread=False)
        self.settings_cursor = self.settings_db.cursor()
        self.alliance_db = sqlite3.connect('db/alliance.sqlite', check_same_thread=False)
        self.c_alliance = self.alliance_db.cursor()
        self.setup_database()

    def get_current_version(self):
        """Get current version from version file"""
        try:
            if os.path.exists("version"):
                with open("version", "r") as f:
                    return f.read().strip()
            return "v0.0.0"
        except Exception:
            return "v0.0.0"
        
    def setup_database(self):
        try:
            self.settings_cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin (
                    id INTEGER PRIMARY KEY,
                    is_initial INTEGER DEFAULT 0
                )
            """)
            
            self.settings_cursor.execute("""
                CREATE TABLE IF NOT EXISTS adminserver (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin INTEGER NOT NULL,
                    alliances_id INTEGER NOT NULL,
                    FOREIGN KEY (admin) REFERENCES admin(id),
                    UNIQUE(admin, alliances_id)
                )
            """)
            
            self.settings_db.commit()
                
        except Exception as e:
            pass

    # --- Helpers: Mongo-first with SQLite fallback for admin and alliance data ---
    def _mongo_admin_enabled(self) -> bool:
        try:
            return bool(AdminAdapter) and bool(os.getenv('MONGO_URI'))
        except Exception:
            return False

    def _is_global_admin(self, user_id: int) -> bool:
        # Mongo-backed check
        try:
            if self._mongo_admin_enabled():
                admins = AdminAdapter.get_admins() or []
                for aid, is_initial in admins:
                    if int(aid) == int(user_id) and int(is_initial) == 1:
                        return True
                return False
        except Exception:
            pass

        # SQLite fallback
        try:
            self.settings_cursor.execute("SELECT is_initial FROM admin WHERE id = ?", (user_id,))
            r = self.settings_cursor.fetchone()
            return bool(r and int(r[0]) == 1)
        except Exception:
            return False

    def _get_admins(self):
        # Returns list of tuples (admin_id, is_initial)
        try:
            if self._mongo_admin_enabled():
                return AdminAdapter.get_admins() or []
        except Exception:
            pass
        try:
            self.settings_cursor.execute("SELECT id, is_initial FROM admin ORDER BY is_initial DESC, id")
            return self.settings_cursor.fetchall() or []
        except Exception:
            return []

    def _add_admin(self, user_id: int) -> bool:
        try:
            if self._mongo_admin_enabled():
                return AdminAdapter.add_admin(int(user_id), 0)
        except Exception:
            pass
        try:
            self.settings_cursor.execute("""
                INSERT OR IGNORE INTO admin (id, is_initial)
                VALUES (?, 0)
            """, (user_id,))
            self.settings_db.commit()
            return True
        except Exception:
            return False

    def _assign_admin_to_alliance(self, admin_id: int, alliance_id: int) -> bool:
        try:
            if self._mongo_admin_enabled() and AdminAssignmentsAdapter:
                return AdminAssignmentsAdapter.add_assignment(int(admin_id), int(alliance_id))
        except Exception:
            pass
        try:
            with sqlite3.connect('db/settings.sqlite') as settings_db:
                cursor = settings_db.cursor()
                cursor.execute("""
                    INSERT INTO adminserver (admin, alliances_id)
                    VALUES (?, ?)
                """, (admin_id, alliance_id))
                settings_db.commit()
                return True
        except Exception:
            return False

    def _remove_admin(self, admin_id: int) -> bool:
        try:
            if self._mongo_admin_enabled():
                ok = AdminAdapter.remove_admin(int(admin_id))
                if AdminAssignmentsAdapter:
                    try:
                        AdminAssignmentsAdapter.clear_admin(int(admin_id))
                    except Exception:
                        pass
                return ok
        except Exception:
            pass
        try:
            self.settings_cursor.execute("DELETE FROM adminserver WHERE admin = ?", (admin_id,))
            self.settings_cursor.execute("DELETE FROM admin WHERE id = ?", (admin_id,))
            self.settings_db.commit()
            return True
        except Exception:
            return False

    def _get_alliances_with_counts(self):
        # Returns list of tuples: (alliance_id, name, member_count)
        # Try Mongo metadata + members first
        try:
            if mongo_ad and mongo_ad.mongo_enabled():
                alliances_meta = None
                if hasattr(mongo_ad, 'AllianceMetadataAdapter'):
                    alliances_meta = getattr(mongo_ad, 'AllianceMetadataAdapter').get_metadata('alliances') or {}
                members = []
                try:
                    if hasattr(mongo_ad, 'AllianceMembersAdapter'):
                        members = getattr(mongo_ad, 'AllianceMembersAdapter').get_all_members() or []
                except Exception:
                    members = []

                out = []
                # alliances_meta may be dict keyed by alliance_id -> {name: ...}
                if isinstance(alliances_meta, dict) and alliances_meta:
                    for k, v in alliances_meta.items():
                        try:
                            aid = int(k)
                        except Exception:
                            try:
                                aid = int(v.get('id'))
                            except Exception:
                                continue
                        name = v.get('name') or str(aid)
                        count = 0
                        try:
                            count = sum(1 for d in members if int(d.get('alliance') or d.get('alliance_id') or 0) == aid)
                        except Exception:
                            count = 0
                        out.append((aid, name, count))
                    # Sort by name
                    out.sort(key=lambda x: (x[1] or '').lower())
                    return out
        except Exception:
            pass

        # SQLite fallback
        try:
            self.c_alliance.execute("SELECT alliance_id, name FROM alliance_list ORDER BY name")
            alliances = self.c_alliance.fetchall() or []
            out = []
            for alliance_id, name in alliances:
                with sqlite3.connect('db/users.sqlite') as users_db:
                    cursor = users_db.cursor()
                    cursor.execute("SELECT COUNT(*) FROM users WHERE alliance = ?", (alliance_id,))
                    member_count = int(cursor.fetchone()[0])
                out.append((alliance_id, name, member_count))
            return out
        except Exception:
            return []

    def __del__(self):
        try:
            self.settings_db.close()
            self.alliance_db.close()
        except:
            pass

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type == discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id", "")
        
        if custom_id == "bot_operations":
            return
        
        if custom_id == "alliance_control_messages":
            try:
                self.settings_cursor.execute("SELECT is_initial FROM admin WHERE id = ?", (interaction.user.id,))
                result = self.settings_cursor.fetchone()
                
                if not result or result[0] != 1:
                    await interaction.response.send_message(
                        "❌ Only global administrators can use this command.", 
                        ephemeral=True
                    )
                    return

                self.settings_cursor.execute("SELECT value FROM auto LIMIT 1")
                result = self.settings_cursor.fetchone()
                current_value = result[0] if result else 1

                embed = discord.Embed(
                    title="💬 Alliance Control Messages Settings",
                    description=f"Alliance Control Information Message is Currently {'On' if current_value == 1 else 'Off'}",
                    color=discord.Color.green() if current_value == 1 else discord.Color.red()
                )

                view = discord.ui.View()
                
                open_button = discord.ui.Button(
                    label="Turn On",
                    emoji="✅",
                    style=discord.ButtonStyle.success,
                    custom_id="control_messages_open",
                    disabled=current_value == 1
                )
                
                close_button = discord.ui.Button(
                    label="Turn Off",
                    emoji="❌",
                    style=discord.ButtonStyle.danger,
                    custom_id="control_messages_close",
                    disabled=current_value == 0
                )

                async def open_callback(button_interaction: discord.Interaction):
                    self.settings_cursor.execute("UPDATE auto SET value = 1")
                    self.settings_db.commit()
                    
                    embed.description = "Alliance Control Information Message Turned On"
                    embed.color = discord.Color.green()
                    
                    open_button.disabled = True
                    close_button.disabled = False
                    
                    await button_interaction.response.edit_message(embed=embed, view=view)

                async def close_callback(button_interaction: discord.Interaction):
                    self.settings_cursor.execute("UPDATE auto SET value = 0")
                    self.settings_db.commit()
                    
                    embed.description = "Alliance Control Information Message Turned Off"
                    embed.color = discord.Color.red()
                    
                    open_button.disabled = False
                    close_button.disabled = True
                    
                    await button_interaction.response.edit_message(embed=embed, view=view)

                open_button.callback = open_callback
                close_button.callback = close_callback

                view.add_item(open_button)
                view.add_item(close_button)

                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

            except Exception as e:
                print(f"Alliance control messages error: {e}")
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while managing alliance control messages.",
                        ephemeral=True
                    )
                    
        elif custom_id in ["assign_alliance", "add_admin", "remove_admin", "main_menu", "bot_status", "bot_settings"]:
            try:
                if custom_id == "assign_alliance":
                    try:
                        # Permission check via Mongo-first, fallback to SQLite
                        if not self._is_global_admin(interaction.user.id):
                            await interaction.response.send_message(
                                "❌ Only global administrators can use this command.", 
                                ephemeral=True
                            )
                            return

                        admins = self._get_admins()

                        if not admins:
                            await interaction.response.send_message(
                                "❌ No administrators found.", 
                                ephemeral=True
                            )
                            return

                            admin_options = []
                            for admin_id, is_initial in admins:
                                try:
                                    user = await self.bot.fetch_user(admin_id)
                                    admin_name = f"{user.name} ({admin_id})"
                                except Exception as e:
                                    admin_name = f"Unknown User ({admin_id})"
                                
                                admin_options.append(
                                    discord.SelectOption(
                                        label=admin_name[:100],
                                        value=str(admin_id),
                                        description=f"{'Global Admin' if is_initial == 1 else 'Server Admin'}",
                                        emoji="👑" if is_initial == 1 else "👤"
                                    )
                                )

                            admin_embed = discord.Embed(
                                title="👤 Admin Selection",
                                description=(
                                    "Please select an administrator to assign alliance:\n\n"
                                    "**Administrator List**\n"
                                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                                    "Select an administrator from the list below:\n"
                                ),
                                color=discord.Color.blue()
                            )

                            admin_select = discord.ui.Select(
                                placeholder="Select an administrator...",
                                options=admin_options
                            )
                            
                            admin_view = discord.ui.View()
                            admin_view.add_item(admin_select)

                            async def admin_callback(admin_interaction: discord.Interaction):
                                try:
                                    selected_admin_id = int(admin_select.values[0])

                                    alliances = self._get_alliances_with_counts()

                                    if not alliances:
                                        await admin_interaction.response.send_message(
                                            "❌ No alliances found.", 
                                            ephemeral=True
                                        )
                                        return

                                    alliances_with_counts = []
                                    for item in alliances:
                                        try:
                                            alliance_id, name, member_count = item
                                            alliances_with_counts.append((int(alliance_id), name, int(member_count)))
                                        except Exception:
                                            continue

                                    alliance_embed = discord.Embed(
                                        title="🏰 Alliance Selection",
                                        description=(
                                            "Please select an alliance to assign to the administrator:\n\n"
                                            "**Alliance List**\n"
                                            "━━━━━━━━━━━━━━━━━━━━━━\n"
                                            "Select an alliance from the list below:\n"
                                        ),
                                        color=discord.Color.blue()
                                    )

                                    view = AllianceSelectView(alliances_with_counts, self)
                                    
                                    async def alliance_callback(alliance_interaction: discord.Interaction):
                                        try:
                                            selected_alliance_id = int(view.current_select.values[0])

                                            # Persist assignment (Mongo first)
                                            saved = self._assign_admin_to_alliance(selected_admin_id, selected_alliance_id)
                                            if not saved:
                                                await alliance_interaction.response.send_message(
                                                    "❌ Failed to assign alliance to administrator.",
                                                    ephemeral=True
                                                )
                                                return

                                            # Resolve alliance name
                                            alliance_name = None
                                            try:
                                                if mongo_ad and mongo_ad.mongo_enabled() and hasattr(mongo_ad, 'AllianceMetadataAdapter'):
                                                    meta = getattr(mongo_ad, 'AllianceMetadataAdapter').get_metadata('alliances') or {}
                                                    if isinstance(meta, dict):
                                                        v = meta.get(str(selected_alliance_id))
                                                        if v:
                                                            alliance_name = v.get('name')
                                            except Exception:
                                                pass
                                            if not alliance_name:
                                                try:
                                                    with sqlite3.connect('db/alliance.sqlite') as alliance_db:
                                                        cursor = alliance_db.cursor()
                                                        cursor.execute("SELECT name FROM alliance_list WHERE alliance_id = ?", (selected_alliance_id,))
                                                        r = cursor.fetchone()
                                                        alliance_name = r[0] if r else str(selected_alliance_id)
                                                except Exception:
                                                    alliance_name = str(selected_alliance_id)
                                            try:
                                                admin_user = await self.bot.fetch_user(selected_admin_id)
                                                admin_name = admin_user.name
                                            except:
                                                admin_name = f"Unknown User ({selected_admin_id})"

                                            success_embed = discord.Embed(
                                                title="✅ Alliance Assigned",
                                                description=(
                                                    f"Successfully assigned alliance to administrator:\n\n"
                                                    f"👤 **Administrator:** {admin_name}\n"
                                                    f"🆔 **Admin ID:** {selected_admin_id}\n"
                                                    f"🏰 **Alliance:** {alliance_name}\n"
                                                    f"🆔 **Alliance ID:** {selected_alliance_id}"
                                                ),
                                                color=discord.Color.green()
                                            )
                                            
                                            if not alliance_interaction.response.is_done():
                                                await alliance_interaction.response.edit_message(
                                                    embed=success_embed,
                                                    view=None
                                                )
                                            else:
                                                await alliance_interaction.message.edit(
                                                    embed=success_embed,
                                                    view=None
                                                )
                                            
                                        except Exception as e:
                                            print(f"Alliance callback error: {e}")
                                            if not alliance_interaction.response.is_done():
                                                await alliance_interaction.response.send_message(
                                                    "❌ An error occurred while assigning the alliance.",
                                                    ephemeral=True
                                                )
                                            else:
                                                await alliance_interaction.followup.send(
                                                    "❌ An error occurred while assigning the alliance.",
                                                    ephemeral=True
                                                )

                                    view.callback = alliance_callback
                                    
                                    if not admin_interaction.response.is_done():
                                        await admin_interaction.response.edit_message(
                                            embed=alliance_embed,
                                            view=view
                                        )
                                    else:
                                        await admin_interaction.message.edit(
                                            embed=alliance_embed,
                                            view=view
                                        )

                                except Exception as e:
                                    print(f"Admin callback error: {e}")
                                    if not admin_interaction.response.is_done():
                                        await admin_interaction.response.send_message(
                                            "An error occurred while processing your request.",
                                            ephemeral=True
                                        )
                                    else:
                                        await admin_interaction.followup.send(
                                            "An error occurred while processing your request.",
                                            ephemeral=True
                                        )

                            admin_select.callback = admin_callback
                            
                            try:
                                await interaction.response.send_message(
                                    embed=admin_embed,
                                    view=admin_view,
                                    ephemeral=True
                                )
                            except Exception as e:
                                await interaction.followup.send(
                                    "An error occurred while sending the initial message.",
                                    ephemeral=True
                                )

                    except Exception as e:
                        try:
                            await interaction.response.send_message(
                                "An error occurred while processing your request.",
                                ephemeral=True
                            )
                        except:
                            pass
                elif custom_id == "add_admin":
                    try:
                        # Mongo-first permission check
                        if not self._is_global_admin(interaction.user.id):
                            await interaction.response.send_message(
                                "❌ Only global administrators can use this command", 
                                ephemeral=True
                            )
                            return

                        await interaction.response.send_message(
                            "Please tag the admin you want to add (@user).", 
                            ephemeral=True
                        )

                        def check(m):
                            return m.author.id == interaction.user.id and len(m.mentions) == 1

                        try:
                            message = await self.bot.wait_for('message', timeout=30.0, check=check)
                            new_admin = message.mentions[0]
                            
                            await message.delete()
                            
                            ok = self._add_admin(new_admin.id)
                            if not ok:
                                await interaction.edit_original_response(
                                    content="❌ Failed to add administrator.",
                                    embed=None
                                )
                                return

                            success_embed = discord.Embed(
                                title="✅ Administrator Successfully Added",
                                description=(
                                    f"**New Administrator Information**\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"👤 **Name:** {new_admin.name}\n"
                                    f"🆔 **Discord ID:** {new_admin.id}\n"
                                    f"📅 **Account Creation Date:** {new_admin.created_at.strftime('%d/%m/%Y')}\n"
                                ),
                                color=discord.Color.green()
                            )
                            success_embed.set_thumbnail(url=new_admin.display_avatar.url)
                            
                            await interaction.edit_original_response(
                                content=None,
                                embed=success_embed
                            )

                        except asyncio.TimeoutError:
                            await interaction.edit_original_response(
                                content="❌ Timeout No user has been tagged.",
                                embed=None
                            )

                    except Exception as e:
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                "❌ An error occurred while adding an administrator.",
                                ephemeral=True
                            )

                elif custom_id == "remove_admin":
                    try:
                        if not self._is_global_admin(interaction.user.id):
                            await interaction.response.send_message(
                                "❌ Only global administrators can use this command.", 
                                ephemeral=True
                            )
                            return
                        admins = self._get_admins()

                        if not admins:
                            await interaction.response.send_message(
                                "❌ No administrator registered in the system.", 
                                ephemeral=True
                            )
                            return

                        admin_select_embed = discord.Embed(
                            title="👤 Administrator Deletion",
                            description=(
                                "Select the administrator you want to delete:\n\n"
                                "**Administrator List**\n"
                                "━━━━━━━━━━━━━━━━━━━━━━\n"
                            ),
                            color=discord.Color.red()
                        )

                        options = []
                        for admin_id, is_initial in admins:
                            try:
                                user = await self.bot.fetch_user(admin_id)
                                admin_name = f"{user.name}"
                            except:
                                admin_name = "Unknown User"

                            options.append(
                                discord.SelectOption(
                                    label=f"{admin_name[:50]}",
                                    value=str(admin_id),
                                    description=f"{'Global Admin' if is_initial == 1 else 'Server Admin'} - ID: {admin_id}",
                                    emoji="👑" if is_initial == 1 else "👤"
                                )
                            )
                        
                        admin_select = discord.ui.Select(
                            placeholder="Select the administrator you want to delete...",
                            options=options,
                            custom_id="admin_select"
                        )

                        admin_view = discord.ui.View(timeout=None)
                        admin_view.add_item(admin_select)

                        async def admin_callback(select_interaction: discord.Interaction):
                            try:
                                selected_admin_id = int(select_interaction.data["values"][0])
                                
                                # Admin info tuple (id, is_initial)
                                admin_info = next(((aid, is_init) for aid, is_init in admins if int(aid) == int(selected_admin_id)), (selected_admin_id, 0))

                                # Fetch alliances assigned to admin
                                admin_alliances = []
                                try:
                                    if self._mongo_admin_enabled() and AdminAssignmentsAdapter:
                                        admin_alliances = [(aid,) for aid in AdminAssignmentsAdapter.get_admin_alliances(int(selected_admin_id))]
                                except Exception:
                                    admin_alliances = []
                                if not admin_alliances:
                                    try:
                                        self.settings_cursor.execute("""
                                            SELECT alliances_id FROM adminserver WHERE admin = ?
                                        """, (selected_admin_id,))
                                        admin_alliances = self.settings_cursor.fetchall() or []
                                    except Exception:
                                        admin_alliances = []

                                alliance_names = []
                                if admin_alliances: 
                                    alliance_ids = [alliance[0] for alliance in admin_alliances]
                                    
                                    # Resolve alliance names via Mongo metadata first
                                    alliance_names = []
                                    resolved = False
                                    try:
                                        if mongo_ad and mongo_ad.mongo_enabled() and hasattr(mongo_ad, 'AllianceMetadataAdapter'):
                                            meta = getattr(mongo_ad, 'AllianceMetadataAdapter').get_metadata('alliances') or {}
                                            if isinstance(meta, dict):
                                                for aid in alliance_ids:
                                                    v = meta.get(str(aid))
                                                    if v and v.get('name'):
                                                        alliance_names.append(v.get('name'))
                                                resolved = True
                                    except Exception:
                                        pass
                                    if not resolved:
                                        try:
                                            alliance_cursor = self.alliance_db.cursor()
                                            placeholders = ','.join('?' * len(alliance_ids))
                                            query = f"SELECT alliance_id, name FROM alliance_list WHERE alliance_id IN ({placeholders})"
                                            alliance_cursor.execute(query, alliance_ids)
                                            alliance_results = alliance_cursor.fetchall()
                                            alliance_names = [alliance[1] for alliance in alliance_results]
                                        except Exception:
                                            alliance_names = []

                                try:
                                    user = await self.bot.fetch_user(selected_admin_id)
                                    admin_name = user.name
                                    avatar_url = user.display_avatar.url
                                except Exception as e:
                                    admin_name = f"Bilinmeyen Kullanıcı ({selected_admin_id})"
                                    avatar_url = None

                                info_embed = discord.Embed(
                                    title="⚠️ Administrator Deletion Confirmation",
                                    description=(
                                        f"**Administrator Information**\n"
                                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"👤 **Name:** `{admin_name}`\n"
                                        f"🆔 **Discord ID:** `{selected_admin_id}`\n"
                                        f"👤 **Access Level:** `{'Global Admin' if admin_info[1] == 1 else 'Server Admin'}`\n"
                                        f"🔍 **Access Type:** `{'All Alliances' if admin_info[1] == 1 else 'Server + Special Access'}`\n"
                                        f"📊 **Available Alliances:** `{len(alliance_names)}`\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━\n"
                                    ),
                                    color=discord.Color.yellow()
                                )

                                if alliance_names:
                                    info_embed.add_field(
                                        name="🏰 Alliances Authorized",
                                        value="\n".join([f"• {name}" for name in alliance_names[:10]]) + 
                                              ("\n• ..." if len(alliance_names) > 10 else ""),
                                        inline=False
                                    )
                                else:
                                    info_embed.add_field(
                                        name="🏰 Alliances Authorized",
                                        value="This manager does not yet have an authorized alliance.",
                                        inline=False
                                    )

                                if avatar_url:
                                    info_embed.set_thumbnail(url=avatar_url)

                                confirm_view = discord.ui.View()
                                
                                confirm_button = discord.ui.Button(
                                    label="Confirm", 
                                    style=discord.ButtonStyle.danger,
                                    custom_id="confirm_remove"
                                )
                                cancel_button = discord.ui.Button(
                                    label="Cancel", 
                                    style=discord.ButtonStyle.secondary,
                                    custom_id="cancel_remove"
                                )

                                async def confirm_callback(button_interaction: discord.Interaction):
                                    try:
                                        ok = self._remove_admin(int(selected_admin_id))
                                        if not ok:
                                            await button_interaction.response.send_message(
                                                "❌ Failed to delete administrator.",
                                                ephemeral=True
                                            )
                                            return

                                        success_embed = discord.Embed(
                                            title="✅ Administrator Deleted Successfully",
                                            description=(
                                                f"**Deleted Administrator**\n"
                                                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                                                f"👤 **Name:** `{admin_name}`\n"
                                                f"🆔 **Discord ID:** `{selected_admin_id}`\n"
                                            ),
                                            color=discord.Color.green()
                                        )
                                        
                                        await button_interaction.response.edit_message(
                                            embed=success_embed,
                                            view=None
                                        )
                                    except Exception as e:
                                        await button_interaction.response.send_message(
                                            "❌ An error occurred while deleting the administrator.",
                                            ephemeral=True
                                        )

                                async def cancel_callback(button_interaction: discord.Interaction):
                                    cancel_embed = discord.Embed(
                                        title="❌ Process Canceled",
                                        description="Administrator deletion canceled.",
                                        color=discord.Color.red()
                                    )
                                    await button_interaction.response.edit_message(
                                        embed=cancel_embed,
                                        view=None
                                    )

                                confirm_button.callback = confirm_callback
                                cancel_button.callback = cancel_callback

                                confirm_view.add_item(confirm_button)
                                confirm_view.add_item(cancel_button)

                                await select_interaction.response.edit_message(
                                    embed=info_embed,
                                    view=confirm_view
                                )

                            except Exception as e:
                                await select_interaction.response.send_message(
                                    "❌ An error occurred during processing.",
                                    ephemeral=True
                                )

                        admin_select.callback = admin_callback

                        await interaction.response.send_message(
                            embed=admin_select_embed,
                            view=admin_view,
                            ephemeral=True
                        )

                    except Exception as e:
                        print(f"Remove admin error: {e}")
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                "❌ An error occurred during the administrator deletion process.",
                                ephemeral=True
                            )

                elif custom_id == "main_menu":
                    try:
                        alliance_cog = self.bot.get_cog("Alliance")
                        if alliance_cog:
                            await alliance_cog.show_main_menu(interaction)
                        else:
                            await interaction.response.send_message(
                                "❌ Ana menüye dönüş sırasında bir hata oluştu.",
                                ephemeral=True
                            )
                    except Exception as e:
                        print(f"[ERROR] Main Menu error in bot operations: {e}")
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                "An error occurred while returning to main menu.", 
                                ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                "An error occurred while returning to main menu.",
                                ephemeral=True
                            )

            except Exception as e:
                if not interaction.response.is_done():
                    print(f"Error processing {custom_id}: {e}")
                    await interaction.response.send_message(
                        "An error occurred while processing your request.",
                        ephemeral=True
                    )

        elif custom_id == "view_admin_permissions":
            try:
                # Permission check
                if not self._is_global_admin(interaction.user.id):
                    await interaction.response.send_message(
                        "❌ Only global administrators can use this command.", 
                        ephemeral=True
                    )
                    return

                # Build admin->alliance permissions list via Mongo first
                admin_permissions = []  # tuples of (admin_id, is_initial, alliance_id)
                admins = self._get_admins()
                if self._mongo_admin_enabled() and AdminAssignmentsAdapter:
                    try:
                        for aid, is_init in admins:
                            alliances = AdminAssignmentsAdapter.get_admin_alliances(int(aid))
                            for al in alliances:
                                admin_permissions.append((int(aid), int(is_init), int(al)))
                    except Exception:
                        admin_permissions = []
                if not admin_permissions:
                    try:
                        with sqlite3.connect('db/settings.sqlite') as settings_db:
                            cursor = settings_db.cursor()
                            cursor.execute("""
                                SELECT a.id, a.is_initial, admin_server.alliances_id
                                FROM admin a
                                JOIN adminserver admin_server ON a.id = admin_server.admin
                                ORDER BY a.is_initial DESC, a.id
                            """)
                            admin_permissions = cursor.fetchall() or []
                    except Exception:
                        admin_permissions = []

                        if not admin_permissions:
                            await interaction.response.send_message(
                                "No admin permissions found.", 
                                ephemeral=True
                            )
                            return

                        admin_alliance_info = []
                        for admin_id, is_initial, alliance_id in admin_permissions:
                            # Resolve name via Mongo metadata first
                            alliance_name = None
                            try:
                                if mongo_ad and mongo_ad.mongo_enabled() and hasattr(mongo_ad, 'AllianceMetadataAdapter'):
                                    meta = getattr(mongo_ad, 'AllianceMetadataAdapter').get_metadata('alliances') or {}
                                    v = meta.get(str(alliance_id)) if isinstance(meta, dict) else None
                                    if v:
                                        alliance_name = v.get('name')
                            except Exception:
                                pass
                            if not alliance_name:
                                try:
                                    self.c_alliance.execute("SELECT name FROM alliance_list WHERE alliance_id = ?", (alliance_id,))
                                    r = self.c_alliance.fetchone()
                                    alliance_name = r[0] if r else str(alliance_id)
                                except Exception:
                                    alliance_name = str(alliance_id)
                            admin_alliance_info.append((admin_id, is_initial, alliance_id, alliance_name))

                        embed = discord.Embed(
                            title="👥 Admin Alliance Permissions",
                            description=(
                                "Select an admin to view or modify permissions:\n\n"
                                "**Admin List**\n"
                                "━━━━━━━━━━━━━━━━━━━━━━\n"
                            ),
                            color=discord.Color.blue()
                        )

                        options = []
                        for admin_id, is_initial, alliance_id, alliance_name in admin_alliance_info:
                            try:
                                user = await interaction.client.fetch_user(admin_id)
                                admin_name = user.name
                            except:
                                admin_name = f"Unknown User ({admin_id})"

                            option_label = f"{admin_name[:50]}"
                            option_desc = f"Alliance: {alliance_name[:50]}"
                            
                            options.append(
                                discord.SelectOption(
                                    label=option_label,
                                    value=f"{admin_id}:{alliance_id}",
                                    description=option_desc,
                                    emoji="👑" if is_initial == 1 else "👤"
                                )
                            )

                        if not options:
                            await interaction.response.send_message(
                                "No admin-alliance permissions found.", 
                                ephemeral=True
                            )
                            return

                        select = discord.ui.Select(
                            placeholder="Select an admin to remove permission...",
                            options=options,
                            custom_id="admin_permission_select"
                        )

                        async def select_callback(select_interaction: discord.Interaction):
                            try:
                                admin_id, alliance_id = select.values[0].split(":")
                                
                                confirm_embed = discord.Embed(
                                    title="⚠️ Confirm Permission Removal",
                                    description=(
                                        f"Are you sure you want to remove the alliance permission?\n\n"
                                        f"**Admin:** {admin_name} ({admin_id})\n"
                                        f"**Alliance:** {alliance_name} ({alliance_id})"
                                    ),
                                    color=discord.Color.yellow()
                                )

                                confirm_view = discord.ui.View()
                                
                                async def confirm_callback(confirm_interaction: discord.Interaction):
                                    try:
                                        # Remove assignment via Mongo-first, fallback to SQLite
                                        success = False
                                        try:
                                            if self._mongo_admin_enabled() and AdminAssignmentsAdapter:
                                                success = AdminAssignmentsAdapter.remove_assignment(int(admin_id), int(alliance_id))
                                        except Exception:
                                            success = False
                                        if not success:
                                            try:
                                                with sqlite3.connect('db/settings.sqlite') as settings_db:
                                                    cursor = settings_db.cursor()
                                                    cursor.execute("DELETE FROM adminserver WHERE admin = ? AND alliances_id = ?", (int(admin_id), int(alliance_id)))
                                                    settings_db.commit()
                                                    success = cursor.rowcount > 0
                                            except Exception:
                                                success = False
                                        
                                        if success:
                                            success_embed = discord.Embed(
                                                title="✅ Permission Removed",
                                                description=(
                                                    f"Successfully removed alliance permission:\n\n"
                                                    f"**Admin:** {admin_name} ({admin_id})\n"
                                                    f"**Alliance:** {alliance_name} ({alliance_id})"
                                                ),
                                                color=discord.Color.green()
                                            )
                                            await confirm_interaction.response.edit_message(
                                                embed=success_embed,
                                                view=None
                                            )
                                        else:
                                            await confirm_interaction.response.send_message(
                                                "An error occurred while removing the permission.",
                                                ephemeral=True
                                            )
                                    except Exception as e:
                                        print(f"Confirm callback error: {e}")
                                        await confirm_interaction.response.send_message(
                                            "An error occurred while removing the permission.",
                                            ephemeral=True
                                        )

                                async def cancel_callback(cancel_interaction: discord.Interaction):
                                    cancel_embed = discord.Embed(
                                        title="❌ Operation Cancelled",
                                        description="Permission removal has been cancelled.",
                                        color=discord.Color.red()
                                    )
                                    await cancel_interaction.response.edit_message(
                                        embed=cancel_embed,
                                        view=None
                                    )

                                confirm_button = discord.ui.Button(
                                    label="Confirm",
                                    style=discord.ButtonStyle.danger,
                                    custom_id="confirm_remove"
                                )
                                confirm_button.callback = confirm_callback
                                
                                cancel_button = discord.ui.Button(
                                    label="Cancel",
                                    style=discord.ButtonStyle.secondary,
                                    custom_id="cancel_remove"
                                )
                                cancel_button.callback = cancel_callback

                                confirm_view.add_item(confirm_button)
                                confirm_view.add_item(cancel_button)

                                await select_interaction.response.edit_message(
                                    embed=confirm_embed,
                                    view=confirm_view
                                )

                            except Exception as e:
                                print(f"Select callback error: {e}")
                                await select_interaction.response.send_message(
                                    "An error occurred while processing your selection.",
                                    ephemeral=True
                                )

                        select.callback = select_callback
                        
                        view = discord.ui.View()
                        view.add_item(select)

                        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

            except Exception as e:
                print(f"View admin permissions error: {e}")
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "An error occurred while loading admin permissions.",
                        ephemeral=True
                    )

        elif custom_id == "view_administrators":
            try:
                # Permission check via Mongo-first, fallback to SQLite
                if not self._is_global_admin(interaction.user.id):
                    await interaction.response.send_message(
                        "❌ Only global administrators can use this command.", 
                        ephemeral=True
                    )
                    return

                # Fetch admins via Mongo-first helper
                admins = self._get_admins()

                if not admins:
                    await interaction.response.send_message(
                        "❌ No administrators found in the system.", 
                        ephemeral=True
                    )
                    return

                admin_list_embed = discord.Embed(
                    title="👥 Administrator List",
                    description="List of all administrators and their permissions:\n━━━━━━━━━━━━━━━━━━━━━━",
                    color=discord.Color.blue()
                )

                for admin_id, is_initial in admins:
                    try:
                        user = await self.bot.fetch_user(admin_id)
                        admin_name = user.name
                        admin_avatar = user.display_avatar.url

                        # Gather alliance IDs via Mongo-first, fallback to SQLite
                        alliance_ids = []
                        try:
                            if self._mongo_admin_enabled() and AdminAssignmentsAdapter:
                                alliance_ids = AdminAssignmentsAdapter.get_admin_alliances(int(admin_id)) or []
                        except Exception:
                            alliance_ids = []
                        if not alliance_ids:
                            try:
                                self.settings_cursor.execute(
                                    "SELECT alliances_id FROM adminserver WHERE admin = ?",
                                    (admin_id,)
                                )
                                rows = self.settings_cursor.fetchall() or []
                                alliance_ids = [int(r[0]) for r in rows]
                            except Exception:
                                alliance_ids = []

                        alliance_names = []
                        if alliance_ids:
                            # Resolve names via Mongo metadata first
                            names_map = {}
                            try:
                                if mongo_ad and mongo_ad.mongo_enabled() and hasattr(mongo_ad, 'AllianceMetadataAdapter'):
                                    meta = getattr(mongo_ad, 'AllianceMetadataAdapter').get_metadata('alliances') or {}
                                    if isinstance(meta, dict):
                                        for aid in alliance_ids:
                                            v = meta.get(str(aid))
                                            if v and isinstance(v, dict) and 'name' in v:
                                                names_map[int(aid)] = v['name']
                            except Exception:
                                pass
                            # Fallback to SQLite for any unresolved names
                            unresolved = [int(aid) for aid in alliance_ids if int(aid) not in names_map]
                            if unresolved:
                                try:
                                    placeholders = ','.join('?' * len(unresolved))
                                    self.c_alliance.execute(
                                        f"SELECT alliance_id, name FROM alliance_list WHERE alliance_id IN ({placeholders})",
                                        unresolved
                                    )
                                    for row in self.c_alliance.fetchall() or []:
                                        names_map[int(row[0])] = row[1]
                                except Exception:
                                    pass
                            alliance_names = [names_map.get(int(aid), str(aid)) for aid in alliance_ids]

                        admin_info = (
                            f"👤 **Name:** {admin_name}\n"
                            f"🆔 **ID:** {admin_id}\n"
                            f"👑 **Role:** {'Global Admin' if is_initial == 1 else 'Server Admin'}\n"
                            f"🔍 **Access Type:** {'All Alliances' if is_initial == 1 else 'Server + Special Access'}\n"
                        )

                        if alliance_names:
                            alliance_text = "\n".join([f"• {name}" for name in alliance_names[:5]])
                            if len(alliance_names) > 5:
                                alliance_text += f"\n• ... and {len(alliance_names) - 5} more"
                            admin_info += f"🏰 **Managing Alliances:**\n{alliance_text}\n"
                        else:
                            admin_info += "🏰 **Managing Alliances:** No alliances assigned\n"

                        admin_list_embed.add_field(
                            name=f"{'👑' if is_initial == 1 else '👤'} {admin_name}",
                            value=f"{admin_info}\n━━━━━━━━━━━━━━━━━━━━━━",
                            inline=False
                        )

                    except Exception as e:
                        print(f"Error processing admin {admin_id}: {e}")
                        admin_list_embed.add_field(
                            name=f"Unknown User ({admin_id})",
                            value="Error loading administrator information\n━━━━━━━━━━━━━━━━━━━━━━",
                            inline=False
                        )

                view = discord.ui.View()
                view.add_item(discord.ui.Button(
                    label="Back to Bot Operations",
                    emoji="◀️",
                    style=discord.ButtonStyle.secondary,
                    custom_id="bot_operations",
                    row=0
                ))

                await interaction.response.send_message(
                    embed=admin_list_embed,
                    view=view,
                    ephemeral=True
                )

            except Exception as e:
                print(f"View administrators error: {e}")
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while loading administrator list.",
                        ephemeral=True
                    )

        elif custom_id == "transfer_old_database":
            try:
                self.settings_cursor.execute("SELECT is_initial FROM admin WHERE id = ?", (interaction.user.id,))
                result = self.settings_cursor.fetchone()
                
                if not result or result[0] != 1:
                    await interaction.response.send_message(
                        "❌ Only global administrators can use this command.", 
                        ephemeral=True
                    )
                    return

                database_cog = self.bot.get_cog('DatabaseTransfer')
                if database_cog:
                    await database_cog.transfer_old_database(interaction)
                else:
                    await interaction.response.send_message(
                        "❌ Database transfer module not loaded.", 
                        ephemeral=True
                    )

            except Exception as e:
                print(f"Transfer old database error: {e}")
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while transferring the database.",
                        ephemeral=True
                    )

        elif custom_id == "check_updates":
            try:
                self.settings_cursor.execute("SELECT is_initial FROM admin WHERE id = ?", (interaction.user.id,))
                result = self.settings_cursor.fetchone()
                
                if not result or result[0] != 1:
                    await interaction.response.send_message(
                        "❌ Only global administrators can use this command.", 
                        ephemeral=True
                    )
                    return

                current_version, new_version, update_notes, updates_needed = await self.check_for_updates()

                if not current_version or not new_version:
                    await interaction.response.send_message(
                        "❌ Failed to check for updates. Please try again later.", 
                        ephemeral=True
                    )
                    return

                main_embed = discord.Embed(
                    title="🔄 Bot Update Status",
                    color=discord.Color.blue() if not updates_needed else discord.Color.yellow()
                )

                main_embed = discord.Embed(
                    title="🔄 Bot Update Status",
                    color=discord.Color.blue() if not updates_needed else discord.Color.yellow()
                )

                main_embed.add_field(
                    name="Current Version",
                    value=f"`{current_version}`",
                    inline=True
                )

                main_embed.add_field(
                    name="Latest Version",
                    value=f"`{new_version}`",
                    inline=True
                )

                if updates_needed:
                    main_embed.add_field(
                        name="Status",
                        value="🔄 **Update Available**",
                        inline=True
                    )

                    if update_notes:
                        notes_text = "\n".join([f"• {note.lstrip('- *•').strip()}" for note in update_notes[:10]])
                        if len(update_notes) > 10:
                            notes_text += f"\n• ... and more!"
                        
                        main_embed.add_field(
                            name="Release Notes",
                            value=notes_text[:1024],  # Discord field limit
                            inline=False
                        )

                    main_embed.add_field(
                        name="How to Update",
                        value=(
                            "To update to the new version:\n"
                            "🔄 **Restart the bot** (main.py)\n"
                            "✅ Accept the update when prompted\n\n"
                            "The bot will automatically download and install the update."
                        ),
                        inline=False
                    )
                else:
                    main_embed.add_field(
                        name="Status",
                        value="✅ **Up to Date**",
                        inline=True
                    )
                    main_embed.description = "Your bot is running the latest version!"

                await interaction.response.send_message(
                    embed=main_embed,
                    ephemeral=True
                )

            except Exception as e:
                print(f"Check updates error: {e}")
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while checking for updates.",
                        ephemeral=True
                    )

    async def show_bot_operations_menu(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="🤖 Bot Operations",
                description=(
                    "Please choose an operation:\n\n"
                    "**Available Operations**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "👥 **Admin Management**\n"
                    "└ Manage bot administrators\n\n"
                    "🔍 **Admin Permissions**\n"
                    "└ View and manage admin permissions\n\n"
                    "🔄 **Bot Updates**\n"
                    "└ Check and manage updates\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=discord.Color.blue()
            )
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="Add Admin",
                emoji="➕",
                style=discord.ButtonStyle.success,
                custom_id="add_admin",
                row=1
            ))
            view.add_item(discord.ui.Button(
                label="Remove Admin",
                emoji="➖",
                style=discord.ButtonStyle.danger,
                custom_id="remove_admin",
                row=1
            ))
            view.add_item(discord.ui.Button(
                label="View Administrators",
                emoji="👥",
                style=discord.ButtonStyle.primary,
                custom_id="view_administrators",
                row=1
            ))
            view.add_item(discord.ui.Button(
                label="Assign Alliance to Admin",
                emoji="🔗",
                style=discord.ButtonStyle.success,
                custom_id="assign_alliance",
                row=2
            ))
            view.add_item(discord.ui.Button(
                label="Delete Admin Permissions",
                emoji="➖",
                style=discord.ButtonStyle.danger,
                custom_id="view_admin_permissions",
                row=2
            ))
            view.add_item(discord.ui.Button(
                label="Transfer Old Database",
                emoji="🔄",
                style=discord.ButtonStyle.primary,
                custom_id="transfer_old_database",
                row=3
            ))
            view.add_item(discord.ui.Button(
                label="Check for Updates",
                emoji="🔄",
                style=discord.ButtonStyle.primary,
                custom_id="check_updates",
                row=3
            ))
            view.add_item(discord.ui.Button(
                label="Log System",
                emoji="📋",
                style=discord.ButtonStyle.primary,
                custom_id="log_system",
                row=3
            ))
            view.add_item(discord.ui.Button(
                label="Alliance Control Messages",
                emoji="💬",
                style=discord.ButtonStyle.primary,
                custom_id="alliance_control_messages",
                row=3
            ))
            view.add_item(discord.ui.Button(
                label="Main Menu",
                emoji="🏠",
                style=discord.ButtonStyle.secondary,
                custom_id="main_menu",
                row=4
            ))

            await interaction.response.edit_message(embed=embed, view=view)

        except Exception as e:
            if not any(error_code in str(e) for error_code in ["10062", "40060"]):
                print(f"Show bot operations menu error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while showing the menu.",
                    ephemeral=True
                )

    async def confirm_permission_removal(self, admin_id: int, alliance_id: int, confirm_interaction: discord.Interaction):
        try:
            self.settings_cursor.execute("""
                DELETE FROM adminserver 
                WHERE admin = ? AND alliances_id = ?
            """, (admin_id, alliance_id))
            self.settings_db.commit()
            return True
        except Exception as e:
            return False

    async def check_for_updates(self):
        """Check for updates using GitHub releases API"""
        try:
            latest_release_url = "https://api.github.com/repos/whiteout-project/bot/releases/latest"
            
            response = requests.get(latest_release_url, timeout=10)
            if response.status_code != 200:
                return None, None, [], False

            latest_release_data = response.json()
            latest_tag = latest_release_data.get("tag_name", "")
            current_version = self.get_current_version()
            
            if not latest_tag:
                return current_version, None, [], False

            updates_needed = current_version != latest_tag
            
            # Parse release notes
            update_notes = []
            release_body = latest_release_data.get("body", "")
            if release_body:
                for line in release_body.split('\n'):
                    line = line.strip()
                    if line and (line.startswith('-') or line.startswith('*') or line.startswith('•')):
                        update_notes.append(line)

            return current_version, latest_tag, update_notes, updates_needed

        except Exception as e:
            print(f"Error checking for updates: {e}")
            return None, None, [], False

async def setup(bot):
    await bot.add_cog(BotOperations(bot, sqlite3.connect('db/settings.sqlite')))
