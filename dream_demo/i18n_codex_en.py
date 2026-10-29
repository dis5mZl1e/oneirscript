"""Codex field English gaps (2026-10-25).

图鉴详情行的「值」有三类成品句走 ``tr`` 但英文包没登记，英文模式下会原样
吐出中文：

1. ``catalog_registry.ITEM_EFFECT_LABELS`` 的「作用」行——扩展包装备（六主题
   + realm 批）在 2026-10-25 前后成批加入，中文标签随数据一起进表，英文字段
   没有同步补登；其中 library/hospital 的旧件同理。
2. ``data/hospital.py`` 的主动技能名：英文此前只以「技能名｜说明」的整句形式
   落在 ``i18n_content_en/content_materials.py``，图鉴「主动技能」行是逐名取词，
   整句键匹配不上。这里逐名补登，用词与那批整句译文保持一致。
3. 弹体构想名与图书馆专属构想的说明（``data/items``）。

只登记文档里确认过的显示口径，不改任何机制；反应配方名不在此处——那是由
「材料甲 + 材料乙 → 产物」拼出的整句，交给 ``i18n_realms.translate_composed``
按部件拼译。
"""

EN_CODEX = {
    # ---- 扩展包装备「作用」行（catalog_registry.ITEM_EFFECT_LABELS） ----
    # 篡改／构想／爆炸／火焰／电场：实用改写十六件
    "篡改：节用": "Tamper: thrift",
    "篡改：远及": "Tamper: reach",
    "篡改：加力": "Tamper: force",
    "构想：节用": "Construct: thrift",
    "构想：击杀余爆": "Construct: kill afterblast",
    "构想：两步准备": "Construct: two-step prep",
    "构想：外光充能": "Construct: outer-light charge",
    "构想：击杀回流": "Construct: kill refund",
    "构想：扩幅": "Construct: wider radius",
    "构想：软征兆延续": "Construct: longer soft omens",
    "构想：近战刻痕": "Construct: melee mark",
    "构想：点燃": "Construct: ignite",
    "爆炸：加压": "Blast: pressurized",
    "火焰：加温": "Flame: hotter",
    "受击接地": "Grounding on hit",
    "电场：限流": "Field: current limit",
    # 声源与调查批
    "受击诱引": "Lure when hurt",
    "诱引回音分账": "Split lure echo",
    "命中留痕诱引": "Marking lure on hit",
    "薄液面挡一下": "Thin liquid step",
    "封衣：不沾液体": "Sealed suit: no liquid",
    # 光与灯具批
    "半罩：前亮后暗": "Half shade: front lit, rear dark",
    "强光缓冲": "Glare buffer",
    "出手短闪": "Strike flash",
    "双档电量手电": "Two-mode flashlight",
    "背向遮光": "Rear shade",
    "遮片挡光": "Soot shield",
    # terrain：液体与地势工具
    "舀液进真容器": "Scoop into a real container",
    "读邻格高低差": "Read neighbouring heights",
    "把容器挂上承载面": "Hang a container on a surface",
    "步伐更沉（被动）": "Heavier stride (passive)",
    "降一档地势": "Lower the ground one step",
    "短导流出口": "Short spill outlet",
    "只取当前可取液体": "Draw only the drawable liquid",
    "单向泄气出口": "One-way gas vent",
    "沿途漏液": "Leaky bucket",
    "固定小工具": "Mount a small tool",
    "把一份附着剥回脚下": "Fling one attachment back down",
    "把液送上高处": "Pump liquid uphill",
    "两条出口分流": "Two-way split gate",
    "可收起的阻液边界": "Foldable liquid barrier",
    # projectile：弹道工具
    "一发一装": "One round, one load",
    "换弹掉落实弹（被动）": "Dropped rounds (passive)",
    "显示第一拦截物": "Shows the first interceptor",
    "把下一发推重": "Heavier next round",
    "两个真实弹仓": "Two real chambers",
    "空仓改近战": "Empty melee",
    "架稳装填（移动即收）": "Braced reload (stows on move)",
    "退出未发射的实弹": "Unload an unfired round",
    "撞面反折一次": "Bounce off one surface",
    "双发分叉弹道": "Forked two-round shot",
    "换弹中走一步（被动）": "A step while reloading (passive)",
    "回收自己的弹壳": "Recover your own rounds",
    "借镜面开火": "Fire through a mirror",
    "末发强击退": "Hard push on the last round",
    "蜡弹齐射并沉积": "Wax volley with deposits",
    # circuit：电路工具
    "试电：只报一跳连通": "Probe: one-hop continuity",
    "操作电路少沾一次（被动）": "Dry cloth (passive)",
    "拆线并回收导线": "Pull wire and recover it",
    "发一次真实信号": "Send one real signal",
    "信号延后一回合": "Delay a signal one round",
    "用焊料连端口": "Solder a port",
    "刮取固体材料": "Scrape solid material",
    "只滤定下的那一种杂质": "Filter one chosen impurity",
    "接熔料凝成障碍": "Melt-cast into an obstacle",
    "只放行同节奏信号": "Same-rhythm relay",
    "容器隔离一回合": "Sealed crucible for one round",
    "择一接通线路": "Fork one live circuit",
    "攻击留下熔料沉积": "Strike leaves a melt deposit",
    # realm 批：医院／书库专属小件
    "刮掉一份负面附着": "Scrape off one negative attachment",
    "抄下设施的交互条件": "Copies a facility's conditions",
    "沿视线标记已知地形": "Mark known terrain along sight",
    "包住一本学习物": "Wraps one study item",
    "剥离附着存入废料格": "Peel an attachment into scrap",
    "托盘托两件、取一件": "Tray holds two, take one",
    "命中换一回合牵制": "A hit buys one round of pinning",
    "恢复品分期给药": "Staged dosing of restoratives",
    "轮换两条构想对照": "Cycles two construct notes",
    "搬一格低矮障碍": "Push one low obstacle",
    "裁掉残留的边缘一格": "Trim one edge cell of residue",
    "续长纸质残留并锁同类": "Extend paper residue, lock its kind",
    "两份恢复品择一延期": "Defer one of two restoratives",
    "推迟残留末次结算": "Defer a residue's last settle",
    "把恒显边界记成锚点": "Anchor a permanent boundary",
    "收回未耗尽的装置": "Pack an unspent device",
    # 扩展包的消耗品与成长内容（各共用一个 effect 常量，见 catalog_registry）
    "一次性：用掉即失去": "One-shot: gone once used",
    "习得后永久生效": "Permanent once learned",
    # ---- 疗养院主动技能名（data/hospital.py）----
    # 用词与 i18n_content_en/content_materials.py 的「技能名｜说明」整句一致。
    "衣壳针线": "Capsid Thread",
    "有限产尘": "Dust Reserve",
    "菌丝迟线": "Mycelium Delay",
    "注射推进": "Injection Dash",
    "缝合牵引": "Suture Haul",
    "听诊广播": "Stethoscope Broadcast",
    "脑脊滴注": "Spinal Drip",
    "短时菌膜": "Brief Membrane",
    "刀片弧扫": "Blade Arc",
    "局部过曝扫描": "Overexposed Scan",
    "白昼切线": "Daylight Line",
    "净相环洗": "Rinse Ring",
    "回流配液": "Reflux Drip",
    "重开耗材": "Restock",
    # ---- 弹体构想与图书馆专属构想 ----
    "声波弹体": "Sonic Round",
    "习得一个尚未学会的图书馆专属构想；全部学会后恢复10点想象力。":
        "Learn one library-only construct you have not learned yet; once all are learned, "
        "restore 10 Imagination.",
}
