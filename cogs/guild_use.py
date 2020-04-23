import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio, os, datetime

import pymongo
from pymongo import MongoClient

app_string = str(os.environ.get("cluster_app_string"))
cluster = MongoClient(app_string)
db = cluster["guild_data"]

#---------- Variables ------------
from functions import member_limit

#---------- Functions ------------
from functions import has_roles, get_field, detect, find_alias, Leaderboard

def get_subguild(collection_part, subguild_sign):
    out = None
    if collection_part != None and "subguilds" in collection_part:
        user_id_given = "int" in f"{type(subguild_sign)}".lower()

        subguilds = collection_part["subguilds"]
        for subguild in subguilds:
            if user_id_given:
                if f"{subguild_sign}" in subguild["members"]:
                    out = subguild
                    break
            else:
                if subguild["name"] == subguild_sign:
                    out = subguild
                    break
    return out

def anf(user):
    line = f"{user}"
    fsymbs = ">`*_~|"
    out = ""
    for s in line:
        if s in fsymbs:
            out += f"\\{s}"
        else:
            out += s
    return out

def mmorpg_col(col_name):
    colors = {
        "paper": discord.Color.from_rgb(163, 139, 101),
        "canopy": discord.Color.from_rgb(120, 55, 55),
        "sky": discord.Color.from_rgb(131, 171, 198),
        "clover": discord.Color.from_rgb(59, 160, 113),
        "vinous": discord.Color.from_rgb(135, 20, 20),
        "lilac": discord.Color.from_rgb(120, 100, 153),
        "pancake": discord.Color.from_rgb(211, 150, 65)
    }
    return colors[col_name]

def sep_args(text):
    text += " "
    if text[0] != "[":
        i = text.find(" ")
        return (text[:+i], text[+i:].strip())
    else:
        bal = 0
        sep = len(text) - 1
        for i in range(len(text)):
            s = text[i]
            if s == "[":
                bal += 1
            elif s == "]":
                bal -= 1
            if bal == 0:
                sep = i
                break
        return (text[1:sep], text[+sep+1:].strip())

async def read_message(channel, user, t_out, client):
    try:
        msg = await client.wait_for("message", check=lambda message: user.id==message.author.id and channel.id==message.channel.id, timeout=t_out)
    except asyncio.TimeoutError:
        reply=discord.Embed(
            title="🕑 Вы слишком долго не писали",
            description=f"Таймаут: {t_out}",
            color=discord.Color.blurple()
        )
        await channel.send(content=user.mention, embed=reply)
        return "Timeout"
    else:
        return msg

async def give_join_role(member, role_id):
    if role_id != None:
        role = discord.utils.get(member.guild.roles, id = role_id)
        if role != None and role not in member.roles:
            try:
                await member.add_roles(role)
            except Exception:
                pass
    return

async def remove_join_role(member, role_id):
    if role_id != None:
        role = discord.utils.get(member.guild.roles, id = role_id)
        if role != None and role in member.roles:
            try:
                await member.remove_roles(role)
            except Exception:
                pass
    return

async def knock_dm(user, extra_channel, log_emb):
    try:
        await user.send(embed = log_emb)
    except Exception:
        await extra_channel.send(content = f"{user.mention}, не могу отправить лично Вам", embed = log_emb)

class guild_use(commands.Cog):
    def __init__(self, client):
        self.client = client

    #========== Events ===========
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Guild & Stats cog is loaded")
    
    #========= Commands ==========
    @commands.cooldown(1, 30, commands.BucketType.member)
    @commands.command(aliases = ["join-guild", "joinguild", "jg", "join"])
    async def join_guild(self, ctx, *, guild_name):
        pr = ctx.prefix
        collection = db["subguilds"]

        result = collection.find_one(
            {
                "_id": ctx.guild.id,
                "subguilds.name": guild_name
            },
            projection={
                "subguilds.requests": False
            }
        )
        if result is None:
            reply = discord.Embed(
                title = "💢 Упс",
                description = (
                    f"На сервере нет гильдий с названием **{guild_name}**\n"
                    f"Список гильдий: `{pr}guilds`"
                ),
                color = mmorpg_col("vinous")
            )
            await ctx.send(embed = reply)
        else:
            m_lim = get_field(result, "member_limit", default=member_limit)

            subguild = get_subguild(result, guild_name)
            guild_role_id = subguild["role_id"]
            private = subguild["private"]
            total_memb = len(subguild["members"])

            if total_memb >= m_lim:
                reply = discord.Embed(
                    title = "🛠 Гильдия переполнена",
                    description = f"В этой гильдии достигнут максимум участников - {m_lim}",
                    color = mmorpg_col("paper")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

            else:
                result = result["subguilds"]
                user_guild = None
                for sg in result:
                    if f"{ctx.author.id}" in sg["members"]:
                        user_guild = sg["name"]
                        break
                del result

                if guild_name == user_guild:
                    reply = discord.Embed(
                        title = "❌ Ошибка",
                        description = f"Вы уже являетесь членом гильдии **{guild_name}**",
                        color = mmorpg_col("vinous")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)
                
                elif user_guild != None:
                    reply = discord.Embed(
                        title = "🛠 О смене гильдий",
                        description = (
                            f"В данный момент Вы являетесь членом гильдии **{user_guild}**.\n"
                            f"Для того, чтобы войти в другую гильдию, Вам нужно выйти из текущей, однако, **не забывайте**:\n"
                            f"**->** Ваш счётчик опыта обнуляется при выходе.\n"
                            f"Команда для выхода: `{pr}leave-guild`"
                        )
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)

                else:
                    if private and ctx.author.id not in [subguild["leader_id"], subguild["helper_id"]]:
                        collection.find_one_and_update(
                            {"_id": ctx.guild.id, "subguilds.name": guild_name},
                            {"$addToSet": {"subguilds.$.requests": ctx.author.id}},
                            upsert=True
                        )
                        reply = discord.Embed(
                            title = "⏳ Ваш запрос отправлен главе",
                            description = (
                                f"Это закрытая гильдия. Вы станете её участником, как только её глава примет вашу заявку"
                            ),
                            color = mmorpg_col("paper")
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)

                        log = discord.Embed(
                            description = (
                                "Запрос на вступление\n"
                                f"**В гильдию:** {guild_name}\n"
                                f"**С сервера:** {ctx.guild.name}\n"
                                f"**Все запросы:** `{pr}requests Страница {guild_name}`\n"
                                f"**Важно:** используйте команды на соответствующем сервере"
                            )
                        )
                        log.set_author(name = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                        if subguild["leader_id"] != None:
                            leader = ctx.guild.get_member(subguild["leader_id"])
                            self.client.loop.create_task(knock_dm(leader, ctx.channel, log))
                        if subguild["helper_id"] != None:
                            helper = ctx.guild.get_member(subguild["helper_id"])
                            self.client.loop.create_task(knock_dm(helper, ctx.channel, log))

                    else:
                        collection.find_one_and_update(
                            {"_id": ctx.guild.id, "subguilds.name": guild_name},
                            {
                                "$set": {
                                    f"subguilds.$.members.{ctx.author.id}": {
                                        "messages": 0
                                    }
                                }
                            }
                        )
                        collection.find_one_and_update(
                            {"_id": ctx.guild.id, "subguilds.requests": {
                                "$elemMatch": {"$eq": ctx.author.id}
                            }},
                            {"$pull": {"subguilds.$.requests": ctx.author.id}}
                        )

                        await give_join_role(ctx.author, guild_role_id)

                        reply = discord.Embed(
                            title = "✅ Добро пожаловать",
                            description = (
                                f"Вы вступили в гильдию **{guild_name}**\n"
                                f"-> Профиль гильдии: `{pr}guild-info {guild_name}`"
                            ),
                            color = mmorpg_col("clover")
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)

    @commands.cooldown(1, 30, commands.BucketType.member)
    @commands.command(aliases = ["leave-guild", "leaveguild", "lg", "leave"])
    async def leave_guild(self, ctx):
        collection = db["subguilds"]

        result = collection.find_one(
            {
                "_id": ctx.guild.id,
                f"subguilds.members.{ctx.author.id}": {"$exists": True}
            },
            projection={"subguilds.name": True, "subguilds.members": True, "subguilds.role_id": True}
        )
        if result is None:
            reply = discord.Embed(
                title = "❌ Ошибка",
                description = f"Вас нет ни в одной гильдии",
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:
            subguild = get_subguild(result, ctx.author.id)
            guild_name = subguild["name"]
            guild_role_id = subguild["role_id"]
            del result

            no = ["no", "0", "нет"]
            yes = ["yes", "1", "да"]

            warn_emb = discord.Embed(
                title = "🛠 Подтверждение",
                description = (
                    f"**->** Ваш счётчик опыта обнулится, как только Вы покинете гильдию **{guild_name}**.\nПродолжить?\n"
                    f"Напишите `да` или `нет`"
                )
            )
            warn_emb.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            warn = await ctx.send(embed = warn_emb)

            msg = await read_message(ctx.channel, ctx.author, 60, self.client)
            await warn.delete()

            if msg != "Timeout":
                user_reply = msg.content.lower()
                if user_reply in no:
                    await ctx.send("Действие отменено")
                elif user_reply in yes:
                    collection.find_one_and_update(
                        {"_id": ctx.guild.id, "subguilds.name": guild_name},
                        {
                            "$unset": {
                                f"subguilds.$.members.{ctx.author.id}": ""
                            }
                        }
                    )
                    await remove_join_role(ctx.author, guild_role_id)
                    reply = discord.Embed(
                        title = "🚪 Выход",
                        description = f"Вы вышли из гильдии **{guild_name}**"
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["guilds"])
    async def top(self, ctx, filtration = "exp", *, extra = "пустую строку"):
        pr = ctx.prefix
        collection = db["subguilds"]
        filters = {
            "exp": "✨",
            "mentions": "📯",
            "members": "👥",
            "roles": "🎗",
            "reputation": "🔅",
            "rating": "🏆"
        }
        filter_aliases = {
            "exp": ["xp", "опыт"],
            "mentions": ["упоминания", "теги", "pings"],
            "members": ["участников", "численности"],
            "roles": ["роли"],
            "reputation": ["репутация"],
            "rating": ["mixed", "рейтинг"]
        }
        filtration = find_alias(filter_aliases, filtration)

        result = collection.find_one({"_id": ctx.guild.id})
        role = detect.role(ctx.guild, extra)

        if filtration is None:
            reply = discord.Embed(
                title = "❓ Фильтры топа",
                description = (
                    f"> `{pr}top exp`\n"
                    f"> `{pr}top mentions`\n"
                    f"> `{pr}top members`\n"
                    f"> `{pr}top reputation`\n"
                    f"> `{pr}top rating`\n"
                    f"> `{pr}top roles`\n"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        elif filtration == "roles" and role is None:
            reply = discord.Embed(
                title = "💢 Ошибка",
                description = f"Вы ввели {extra}, подразумевая роль, но она не была найдена",
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        elif result is None or not "subguilds" in result:
            lb = discord.Embed(
                title = f"⚔ Гильдии сервера {ctx.guild.name}",
                description = "Отсутствуют",
                color = mmorpg_col("pancake")
            )
            lb.set_thumbnail(url = f"{ctx.guild.icon_url}")
            await ctx.send(embed = lb)
        else:
            subguilds = result["subguilds"]

            stats = []

            if filtration == "rating":
                desc = "Фильтрация одновременно **по опыту и репутации** - рейтинг гильдий"

                total_mes = 0
                total_rep = 0
                for sg in subguilds:
                    total_rep += sg["reputation"]
                    guild_mes = 0
                    for key in sg["members"]:
                        guild_mes += sg["members"][key]["messages"]
                    total_mes += guild_mes
                    stats.append((sg["name"], sg["reputation"], guild_mes))

                if total_rep <= 0:
                    total_rep = 1
                transfer_weight = total_mes / total_rep

                stats = [(pair[0], pair[1] + round(pair[2] / transfer_weight)) for pair in stats]
            
            else:
                for subguild in subguilds:
                    if filtration == "exp":
                        desc = "Фильтрация **по количеству опыта**"
                        total = 0
                        for str_id in subguild["members"]:
                            memb = subguild["members"][str_id]
                            total += memb["messages"]
                    elif filtration == "roles":
                        desc = f"Фильтрация **по количеству участников, имеющих роль <@&{role.id}>**"
                        total = 0
                        for key in subguild["members"]:
                            memb = subguild["members"][key]
                            user_id = int(key)
                            member = ctx.guild.get_member(user_id)
                            if member != None and role in member.roles:
                                total += 1
                    elif filtration == "mentions":
                        desc = "Фильтрация **по количеству упоминаний**"
                        total = subguild["mentions"]
                    elif filtration == "members":
                        desc = "Фильтрация **по количеству участников**"
                        total = len(subguild["members"])
                    elif filtration == "reputation":
                        desc = "Фильтрация **по репутации**"
                        total = subguild["reputation"]

                    pair = (f"{subguild['name']}", total)
                    stats.append(pair)
            
            del result
            lb = Leaderboard(stats)
            lb.sort_values()
            pos = 0

            table = ""
            for pair in lb.pairs:
                pos += 1
                guild_name = anf(pair[0])
                table += f"**{pos})** {guild_name} • **{pair[1]}** {filters[filtration]}\n"
            
            lb = discord.Embed(
                title = f"⚔ Гильдии сервера {ctx.guild.name}",
                description = (
                    f"{desc}\n"
                    f"Подробнее о гильдии: `{pr}guild-info Название`\n"
                    f"Вступить в гильдию: `{pr}join-guild Название`\n\n"
                    f"{table}"
                ),
                color = mmorpg_col("pancake")
            )
            lb.set_thumbnail(url = f"{ctx.guild.icon_url}")
            await ctx.send(embed = lb)

    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.command(aliases = ["global-top", "globaltop", "glt"])
    async def global_top(self, ctx, page="1"):
        collection = db["subguilds"]
        interval = 15

        if not page.isdigit():
            reply = discord.Embed(
                title = "💢 Ошибка",
                description = f"Входной аргумент {page} должен быть целым числом",
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            page = int(page)
            result = collection.find_one(
                {"_id": ctx.guild.id},
                projection={"subguilds.members": True}
            )

            pairs = []
            if result != None and "subguilds" in result:
                for sg in result["subguilds"]:
                    for key in sg["members"]:
                        memb = sg["members"][key]
                        user_id = int(key)
                        pairs.append((user_id, memb["messages"]))
            pairs.sort(key=lambda i: i[1], reverse=True)

            length = len(pairs)
            total_pages = (length-1) // interval + 1
            if page > total_pages:
                reply = discord.Embed(
                    title = "💢 Упс",
                    description = f"Страница не найдена. Всего страниц: **{total_pages}**",
                    color = mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
            
            else:
                place = None
                for i in range(length):
                    if pairs[i][0] == ctx.author.id:
                        place = i
                        break
                if place is None:
                    auth_desc = "Вас нет в этом топе, так как Вы не состоите ни в одной гильдии"
                else:
                    auth_desc = f"Ваше место в топе: **{place+1} / {length}**"
                
                first_num = interval * (page-1)
                last_num = min(length, interval * page)

                desc = ""
                for i in range(first_num, last_num):
                    user = ctx.guild.get_member(pairs[i][0])
                    desc += f"**{i+1})** {anf(user)} • **{pairs[i][1]}** ✨\n"
                
                reply = discord.Embed(
                    title = f"🌐 Топ всех участников гильдий сервера\n{ctx.guild.name}",
                    description = f"{auth_desc}\n\n{desc}",
                    color = mmorpg_col("sky")
                )
                reply.set_thumbnail(url = f"{ctx.guild.icon_url}")
                reply.set_footer(text=f"Стр. {page}/{total_pages} | {ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["guild-info", "guildinfo", "gi"])
    async def guild_info(self, ctx, *, guild_name = None):
        pr = ctx.prefix
        collection = db["subguilds"]

        result = collection.find_one({"_id": ctx.guild.id})
        if guild_name is None:
            subguild = get_subguild(result, ctx.author.id)
            error_text = (
                "Вас нет в какой-либо гильдии, однако, можно посмотреть профиль конкретной гильдии:\n"
                f"`{pr}guild-info Название гильдии`\n"
                f"Список гильдий: `{pr}top`"
            )
        else:
            subguild = get_subguild(result, guild_name)
            error_text = (
                f"На сервере нет гильдий с названием **{guild_name}**\n"
                f"Список гильдий: `{pr}top`"
            )
        del result
            
        if subguild is None:
            reply = discord.Embed(
                title = "💢 Упс",
                description = error_text,
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:

            total_mes = 0
            total_memb = 0
            for str_id in subguild["members"]:
                memb = subguild["members"][str_id]
                total_mes += memb["messages"]
                total_memb += 1
            subguild["members"] = None
            
            reply = discord.Embed(
                title = subguild["name"],
                description = (
                    f"{subguild['description']}\n"
                    f"**->** Топ участников: `{pr}guild-top 1 {subguild['name']}`"
                ),
                color = mmorpg_col("sky")
            )
            reply.set_thumbnail(url = subguild["avatar_url"])
            if subguild['leader_id'] != None:
                leader = ctx.guild.get_member(subguild["leader_id"])
                reply.add_field(name = "💠 Владелец", value = f"> {anf(leader)}", inline=False)
            if subguild['helper_id'] != None:
                helper = ctx.guild.get_member(subguild["helper_id"])
                reply.add_field(name = "🔰 Помощник", value = f"> {anf(helper)}", inline=False)
            reply.add_field(name = "👥 Всего участников", value = f"> {total_memb}", inline=False)
            reply.add_field(name = "✨ Всего опыта", value = f"> {total_mes}", inline=False)
            reply.add_field(name = "🔅 Репутация", value = f"> {subguild['reputation']}", inline=False)
            if subguild["mentions"] > 0:
                reply.add_field(name = "📯 Упоминаний", value = f"> {subguild['mentions']}", inline=False)
            if subguild["role_id"] != None:
                reply.add_field(name = "🎗 Роль", value = f"> <@&{subguild['role_id']}>", inline=False)
            if subguild["private"]:
                reply.add_field(name = "🔒 Приватность", value = "> Вступление по заявкам")
            await ctx.send(embed = reply)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["guild-members", "guildmembers", "gm", "guild-top", "gt"])
    async def guild_members(self, ctx, page_num="1", *, guild_name = None):
        pr = ctx.prefix
        collection = db["subguilds"]
        interval = 15

        if not page_num.isdigit():
            reply = discord.Embed(
                title = "💢 Неверный аргумент",
                description = (
                    f"**{page_num}** должно быть целым числом\n"
                    f"Команда: `{pr}{ctx.command.name} Номер_страницы Гильдия`"
                )
            )
            await ctx.send(embed = reply)
        else:
            page_num = int(page_num)

            result = collection.find_one(
                {"_id": ctx.guild.id},
                projection={
                    "subguilds.name": True,
                    "subguilds.members": True,
                    "subguilds.avatar_url": True
                }
            )
            if guild_name is None:
                subguild = get_subguild(result, ctx.author.id)
                error_text = (
                    "Вас нет в какой-либо гильдии, но Вы можете посмотреть топ конкретной гильдии:\n"
                    f"`{pr}guild-top Страница Название гильдии`"
                )
            else:
                subguild = get_subguild(result, guild_name)
                error_text = (
                    f"На сервере нет гильдий с названием **{guild_name}**\n"
                    f"Список гильдий: `{pr}top`"
                )
            del result

            if subguild is None:
                reply = discord.Embed(
                    title = "💢 Упс",
                    description = error_text,
                    color = mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            else:

                members = subguild["members"]
                total_memb = len(members)
                if interval*(page_num - 1) >= total_memb:
                    reply = discord.Embed(
                        title = "💢 Упс",
                        description = f"Страница не найдена. Всего страниц: **{(total_memb - 1)//interval + 1}**"
                    )
                    await ctx.send(embed = reply)
                else:
                    pairs = []
                    for key in members:
                        member = members[key]
                        user_id = int(key)
                        pairs.append((user_id, member["messages"]))
                    pairs.sort(key=lambda i: i[1], reverse=True)

                    last_num = min(total_memb, interval*page_num)
                    
                    desc = ""
                    for i in range(interval*(page_num-1), last_num):
                        pair = pairs[i]
                        user = ctx.guild.get_member(pair[0])
                        desc += f"**{i + 1})** {anf(user)} • **{pair[1]}** ✨\n"
                    
                    lb = discord.Embed(
                        title = f"👥 Участники гильдии {subguild['name']}",
                        description = desc,
                        color = mmorpg_col("clover")
                    )
                    lb.set_footer(text=f"Стр. {page_num}/{(total_memb - 1)//interval + 1}")
                    lb.set_thumbnail(url = subguild["avatar_url"])
                    await ctx.send(embed = lb)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["user-guild", "userguild", "ug", "user-info", "userinfo", "ui"])
    async def user_guild(self, ctx, user_s = None):
        pr = ctx.prefix
        if user_s is None:
            user = ctx.author
        else:
            user = detect.member(ctx.guild, user_s)
        if user is None:
            reply = discord.Embed(
                title = "💢 Упс",
                description = f"Вы ввели {user_s}, подразумевая участника, но он не был найден",
            )
            await ctx.send(embed = reply)
        else:
            collection = db["subguilds"]
            result = collection.find_one(
                {"_id": ctx.guild.id, f"subguilds.members.{user.id}": {"$exists": True}},
                projection={"subguilds.requests": False}
            )
            if result is None:
                heading = "🛠 Пользователь не в гильдии"
                if user_s is None:
                    heading = "🛠 Вы не в гильдии"
                reply = discord.Embed(
                    title = heading,
                    description = f"Вы можете посмотреть список гильдий здесь: `{pr}guilds`",
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            else:
                subguild = get_subguild(result, user.id)
                del result

                user_mes = subguild["members"][f"{user.id}"]["messages"]
                pairs = [(int(ID), subguild["members"][ID]["messages"]) for ID in subguild["members"]]
                subguild["members"] = {}
                pairs.sort(key=lambda i: i[1], reverse=True)

                place = pairs.index((user.id, user_mes)) + 1

                stat_emb = discord.Embed(color = mmorpg_col("paper"))
                stat_emb.add_field(name="🛡 Гильдия", value=anf(subguild['name']), inline = False)
                stat_emb.add_field(name="✨ Заработано опыта", value=f"{user_mes}", inline = False)
                stat_emb.add_field(name="🏅 Место", value=f"{place} / {len(pairs)}", inline = False)
                stat_emb.set_author(name = f"Профиль 🔎 {user}", icon_url = f"{user.avatar_url}")
                stat_emb.set_thumbnail(url = subguild["avatar_url"])
                await ctx.send(embed = stat_emb)

    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.command(aliases = ["count-roles", "countroles", "cr"])
    async def count_roles(self, ctx, *, text_data):
        pr = ctx.prefix
        collection = db["subguilds"]

        guild_name, text = sep_args(text_data)
        raw_roles = text.split()
        
        result = collection.find_one(
            {"_id": ctx.guild.id, "subguilds.name": guild_name},
            projection={
                "master_role_id": True,
                "subguilds.name": True,
                "subguilds.members": True,
                "subguilds.leader_id": True,
                "subguilds.helper_id": True
            }
        )
        if result is None:
            reply = discord.Embed(
                title = "💢 Упс",
                description = f"На сервере нет гильдии с названием **{guild_name}**",
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        else:
            roles = [detect.role(ctx.guild, s) for s in raw_roles]
            if None in roles or roles == []:
                reply = discord.Embed(
                    title = f"💢 Ошибка",
                    description = (
                        f"В качестве ролей укажите их **@Упоминания** или **ID**\n"
                        f'**Пример:** `{pr}count-roles "{guild_name}" {ctx.guild.default_role.id}`'
                    )
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

            else:
                subguild = get_subguild(result, guild_name)
                pairs = [[r, 0] for r in roles]
                for key in subguild["members"]:
                    user_id = int(key)
                    member = ctx.guild.get_member(user_id)
                    if member != None:
                        for i in range(len(pairs)):
                            role = pairs[i][0]
                            if role in member.roles:
                                pairs[i][1] += 1
                del subguild

                pairs.sort(key=lambda i: i[1])
                desc = ""
                for pair in pairs:
                    desc += f"<@&{pair[0].id}> • {pair[1]} 👥\n"

                reply = discord.Embed(
                    title = guild_name,
                    description = (
                        f"**Статистика ролей:**\n"
                        f"{desc}"
                    ),
                    color = mmorpg_col("paper")
                )
                await ctx.send(embed = reply)
    
    #--------- Errors ----------
    @join_guild.error
    async def join_guild_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    "**Описание:** вход в гильдию\n"
                    f"**Использование:** `{p}{cmd} Название гильдии`\n"
                    f"**Пример:** `{p}{cmd} Короли`"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @count_roles.error
    async def count_roles_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    "**Описание:** подсчитать кол-во перечисленных ролей в существующих гильдиях\n"
                    f"**Использование:** `{p}{cmd} [Гильдия] @роль1 @роль2 ...`\n"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

def setup(client):
    client.add_cog(guild_use(client))