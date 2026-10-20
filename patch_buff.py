import os
import re
import shutil
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "bot.py"

if not os.path.exists(SRC):
    print(f"Lỗi: Không tìm thấy file {SRC}")
    sys.exit(1)

# Tạo bản sao lưu dự phòng
shutil.copy(SRC, SRC + ".bak")
with open(SRC, "r", encoding="utf-8") as f:
    s = f.read()

def rx(name, pat, rep, flags=0):
    global s
    s, n = re.subn(pat, rep, s, flags=flags)
    print(("OK   " if n else "MISS ") + f"{name}: {n}")

def lit(name, old, new):
    global s
    n = s.count(old)
    s = s.replace(old, new)
    print(("OK   " if n else "MISS ") + f"{name}: {n}")

def line_rx(name, must, pat, rep):
    """Chỉ sửa trên những dòng có chứa chuỗi `must`."""
    global s
    n, out = 0, []
    for ln in s.split("\n"):
        if must in ln:
            new = re.sub(pat, rep, ln)
            if new != ln:
                n += 1
            ln = new
        out.append(ln)
    s = "\n".join(out)
    print(("OK   " if n else "MISS ") + f"{name}: {n}")

NUM = r'(?<![A-Za-z0-9])([×x])'

# ============ 1. YUKARI - LAST WORD 2.5x -> 3.0x ============
rx("Yukari LastWord (code)", 
   r'((?:yukari_lastword\w*|y_last)(?:"\])? = True[ \t]*\n[ \t]*\w+ = int\(\w+ \* )2\.5(\))', 
   r'\g<1>3.0\g<2>')
rx("Yukari LastWord (text)", NUM + r'2\.5(?![\d%])', r'\g<1>3.0')

# ============ 2. YUKARI - TRIP TO THE OLD STATION 2.0x -> 2.2x ============
rx("Yukari Station (code)", 
   r'((?:yukari_station\w*|y_station)(?:"\])? = True[ \t]*\n[ \t]*\w+ = int\(\w+ \* )2\.0(\))', 
   r'\g<1>2.2\g<2>')
line_rx("Yukari Station (text)", "Old Station", NUM + r'2\.0', r'\g<1>2.2')

# ============ 3. MARISA - MASTER SPARK 2.0x -> 2.5x ============
rx("Marisa (code)", 
   r'(marisa\w*(?:"\])? = True[ \t]*\n[ \t]*\w+ = int\(\w+ \* )2\.0(\))', 
   r'\g<1>2.5\g<2>')
line_rx("Marisa (text)", "Master Spark", NUM + r'2\.0', r'\g<1>2.5')

# ============ 4. UTSUHO - NUCLEAR SPELL CARD 3.0x -> 3.5x ============
rx("Utsuho (code)", r'(int\(\w+ \* )3\.0(\))', r'\g<1>3.5\g<2>')
rx("Utsuho (text ×3.0)", NUM + r'3\.0(?![\d%])', r'\g<1>3.5')
rx("Utsuho (text 3.0x)", r'(?<![0-9.])3\.0x', '3.5x')

# ============ 5. REIMU - VÔ TƯỞNG CHUYỂN SINH ============
lit("Reimu desc EVOL_CONFIG", 
    "chỉ bảo vệ riêng Reimu).", 
    "chỉ bảo vệ riêng Reimu). Khi kích hoạt còn PHẢN ĐÒN gây thêm 1x ATK lên đối thủ/Boss.")

lit("Reimu desc CHARACTER_DETAILS", 
    "Miễn toàn bộ sát thương 1 lần trong trận (Tỷ lệ đồng nhất 40% cả trong Raid Boss và Battle/PvP)!", 
    "Miễn toàn bộ sát thương 1 lần trong trận và phản đòn 1x ATK (Tỷ lệ đồng nhất 40% cả trong Raid Boss và Battle/PvP)!")

lit("Reimu desc OpponentTeamView", 
    "*Vô Tưởng Chuyển Sinh* né toàn bộ sát thương.", 
    "*Vô Tưởng Chuyển Sinh* né toàn bộ sát thương và phản đòn 1x ATK.")

lit("Reimu desc /evol", 
    "Miễn thương 1 lần trong trận, tỷ lệ 40% cả raid và battle/pvp", 
    "Miễn thương + phản đòn 1x ATK, 1 lần/trận, tỷ lệ 40% cả raid và battle/pvp")

HOOK = '''def reimu_counter_bonus(c, ac):
    """Reimu Ace 2: sau khi Vo Tuong Chuyen Sinh kich hoat -> phan don 1x ATK (tra 1 lan)."""
    try:
        if not c.get("reimu_invul_used"):
            c["reimu_paid"] = False
            return 0, None
        if c.get("reimu_paid"):
            return 0, None
        for k in c.get("team_cards", []):
            if k.get("cid") == 15 and k.get("is_ace2"):
                c["reimu_paid"] = True
                d = int(k["power"])
                return d, f"🌸 **[Ace 2] [#15] reimu** ({c['username']}) - **Vô Tưởng Chuyển Sinh** phản đòn **1x ATK**: +**{d:,} DMG** lên Boss!"
    except Exception as e:
        print(f"[REIMU] loi counter: {e}", flush=True)
    return 0, None

'''

lit("Reimu hook (def)", 
    "def t7_raid_attack(c, ac, card_dmg, boss_stunned, turn_image, notif, active, L):", 
    HOOK + "def t7_raid_attack(c, ac, card_dmg, boss_stunned, turn_image, notif, active, L):")

lit("Reimu hook (raid)", 
    "card_dmg = eq_raid_player_attack(ac, card_dmg, L)", 
    "card_dmg = eq_raid_player_attack(ac, card_dmg, L)\n"
    "    _rb, _rl = reimu_counter_bonus(c, ac)\n"
    "    if _rb:\n"
    "        card_dmg += _rb\n"
    "        notif = (notif + chr(10) if notif else \"\") + _rl")

lit("Reimu hook (Jotaro/Prime)", 
    "dmg = eq_jt_player_attack(ac, dmg, B)", 
    "dmg = eq_jt_player_attack(ac, dmg, B)\n"
    "    _rb, _rl = reimu_counter_bonus(c, ac)\n"
    "    if _rb:\n"
    "        dmg += _rb\n"
    "        notes.append(_rl)")

def inject(name, pat, lines):
    def f(m):
        ind = m.group(2)
        return m.group(1) + ind + m.group(3) + "".join(ind + l + "\n" for l in lines)
    rx(name, pat, f)

inject("Reimu Battle (player)", r'(p_reimu = True\n)([ \t]*)(pc_invul = True\n)', [
    'oc["current_hp"] = max(0, oc["current_hp"] - pc["power"])',
    '''turn_actions.append(f"🌸 **[Ace 2] [#15] reimu** phản đòn **1x ATK**, gây **{pc['power']:,} DMG** lên **{oc['name']}**!")''',
])

inject("Reimu Battle (NPC)", r'(o_reimu = True\n)([ \t]*)(oc_invul = True\n)', [
    'pc["current_hp"] = max(0, pc["current_hp"] - oc["power"])',
    '''turn_actions.append(f"🌸 **Đối thủ [Ace 2] [#15] reimu** phản đòn **1x ATK**, gây **{oc['power']:,} DMG** lên **{pc['name']}**!")''',
])

inject("Reimu PvP (challenger)", r'(c_reimu = True\n)([ \t]*)(c_invul = True\n)', [
    'tc["current_hp"] = max(0, tc["current_hp"] - cc["power"])',
    '''turn_actions.append(f"🌸 **[Ace 2] [#15] reimu** ({challenger.display_name}) phản đòn **1x ATK**, gây **{cc['power']:,} DMG** lên **{tc['name']}**!")''',
])

inject("Reimu PvP (target)", r'(t_reimu = True\n)([ \t]*)(t_invul = True\n)', [
    'cc["current_hp"] = max(0, cc["current_hp"] - tc["power"])',
    '''turn_actions.append(f"🌸 **[Ace 2] [#15] reimu** ({target.display_name}) phản đòn **1x ATK**, gây **{tc['power']:,} DMG** lên **{cc['name']}**!")''',
])

# Story Rumia + Cirno
_story = iter([("rumia_hp", "Rumia"), ("cirno_hp", "Cirno")])
def _story_f(m):
    try:
        var, nm = next(_story)
    except StopIteration:
        return m.group(0)
    ind = m.group(2)
    return (m.group(1) + ind + m.group(3)
            + ind + f'{var} = max(0, {var} - pc["power"])\n'
            + ind + f'turn_logs.append(f"🌸 **[Ace 2] Reimu** phản đòn **1x ATK**, gây **{{pc[\'power\']:,}} DMG** lên {nm}!")\n')

rx("Reimu Story (Rumia + Cirno)", r'((?<!\w)reimu_used = True\n)([ \t]*)(invul = True\n)', _story_f)

def _s3_f(m):
    ind = m.group(2)
    return (m.group(1) + ind + 'B["hp"] = max(0, B["hp"] - pc["power"])\n'
            + ind + '''logs.append(f"🌸 **[Ace 2] [#15] reimu** phản đòn **1x ATK**, gây **{pc['power']:,} DMG** lên Meiling!")\n'''
            + ind)

rx("Reimu Story Stage 3", r'(fl["reimu"] = True\n)([ \t]*)', _s3_f)

# ============ 6. SỬA LỆCH GIF SAKUYA ============
lines = s.split("\n")
n = 0
for i, l in enumerate(lines):
    if 'EVOL_CONFIG[19]["skill_gif"]' in l and any(('sakuya' in x and '= True' in x) for x in lines[max(0, i - 4):i]):
        lines[i] = l.replace('EVOL_CONFIG[19]', 'EVOL_CONFIG[18]')
        n += 1
s = "\n".join(lines)
print(("OK   " if n else "MISS ") + f"Sakuya stun GIF: {n}")

# ============ 7. SỬA LỆCH NHÃN /EVOL ============
lit("Nhãn /evol Reimu", '"[#15] reimu Hakurei (Ace 2 - Cần 20 thẻ)"', '"[#17] Reimu Hakurei (Ace 2 - Cần 20 thẻ)"')

with open(SRC, "w", encoding="utf-8", newline="\n") as f:
    f.write(s)

print("\nXong! Bản sao lưu an toàn tại:", SRC + ".bak")
