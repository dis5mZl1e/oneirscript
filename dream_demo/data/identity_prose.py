"""出生身份的个人痕迹和规则分段。"""

IDENTITY_PROSE = {
    'ordinary': ('枕边有一道熟悉的压痕，醒来时却想不起是谁留下的。', 'A familiar dent marks the pillow, though you cannot recall who left it.'),
    'paper': ('指节的折痕总捋不平，你走过墙角时会下意识侧过身。', 'The creases in your paper knuckles never smooth out; you turn sideways at corners without thinking.'),
    'rain': ('衣袖一直潮着，鞋里却没有水。你记得许多屋檐下的声音。', 'Your sleeves stay damp, yet your shoes hold no water. You remember the sounds beneath many eaves.'),
    'ember': ('指尖留着洗不掉的灰，写字时总给下一行留些空白。', 'Ash never washes from your fingertips; when writing, you always leave space for the next line.'),
    'porcelain': ('瓷壳上补过的地方微微发黄，你记得每一道裂缝。', 'Mended patches in your porcelain shell have yellowed slightly. You remember every crack.'),
    'mirror': ('镜子里的那只手先伸了出来。从那以后，你总慢半拍收手。', 'The hand in the mirror reached out first. Ever since, you have been half a beat late drawing yours back.'),
    'fog': ('雾里的脚步声很熟，你却始终没有回头。', 'The footsteps in the fog sound familiar, but you have never turned around.'),
    'writer': ('签名的位置还空着，笔尖悬在那里，已经许久。', 'The signature line is still blank. Your pen has hovered there for a long time.'),
}

# 先前规则段的英文与数值均保留；此表只用于分出首段。
EN_IDENTITY_PROSE = {zh: en for zh, en in IDENTITY_PROSE.values()}
