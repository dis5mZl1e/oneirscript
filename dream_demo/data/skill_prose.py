"""主梦技能的玩家说明；只替换文字，工作簿和可执行参数仍是原数据。"""

# 每项依次为中文效果、中文条件、英文效果、英文条件。
SKILL_PROSE = {
    'paper_dart': (
        '折起的纸页沿直线飞出，刺中第一个挡路的目标便停下；穿不过高墙，也不会弹回。',
        '它看得见两至四格外的目标，纸页飞出的路线上能击中目标。',
        'A folded page flies straight and stops at the first target it strikes. It cannot pass through high walls or ricochet.',
        'It can see a target two to four cells away, with something it can hit along the line.'),
    'fold_guard': (
        '它把折面挡在身前。两回合内，第一次受击少受一点创伤，仍至少受一点；挡过一次便失效。',
        '它的完整度不高于六成，身前还没有护折。',
        'It raises a folded surface. For two rounds, the first hit deals one less trauma, to a minimum of one; the guard then ends.',
        'Its integrity is at most 60%, and it has no Fold Guard.'),
    'echo_alert': (
        '它喊出刚看见你的位置，声音沿可通的路径传给至多两名同伴。听见呼喊不会让攻击变强。',
        '它看得见你，附近还有尚未听到这处位置的同伴。',
        'It calls out where it last saw you. The sound reaches at most two allies along open sound paths, without strengthening their attacks.',
        'It can see you, and an ally has not yet learned this position.'),
    'model_push': (
        '模型击中后把目标推开一格。若目的地有危险，会先亮出那一格；撞墙不会再添创伤。',
        '目标就在近处，亮出的落点能击中它。',
        'The model pushes a struck target one cell. A dangerous destination is marked in advance; wall collisions add no trauma.',
        'A nearby target can be struck at the marked cell.'),
    'cool_drain': (
        '它抽走落点上的液体与气体，每格各至多八单位；机关需要的材料、任务液体和永久来源仍留着。',
        '影响范围里至少有一格液体或气体可以抽走。',
        'It drains at most eight units each of liquid and gas per cell. Mechanism materials, quest liquids and permanent sources remain.',
        'At least one affected cell contains liquid or gas that can be drained.'),
    'light_trace': (
        '逆光沿亮出的直线划过，只打击一次。你移开以后，光不会跟过来，也不留下额外灼伤。',
        '它看得见两至四格外的目标。',
        'Backlight cuts once along the marked line. It does not follow you after you move or leave extra burns.',
        'It can see a target two to four cells away.'),
    'clock_drag': (
        '脚步落后了半拍：两回合内，每步多耗时零点三回合。攻击和构想照常，也不会让你被迫沉眠。',
        '它看得见你，而你的脚步还没有迟拍。',
        'Your steps fall behind: for two rounds, movement takes 0.3 rounds longer. Attacks and constructs are unaffected; it does not force sleep.',
        'It can see you, and you have no Late Beat.'),
    'mirror_swap': (
        '它从镜侧跟着你走到你身旁的空地，结算时以你当时的位置为准（不锁定起手格）；不会与你交换位置，也不会越过受保护的门。',
        '目标在两至三格外，结算时侧面仍有它看得见且可通行的空位；占住侧面空位或拉开距离都能让它扑空。',
        'It follows you through the mirror side and steps into an empty cell beside your position at resolution (not the cell where it began casting). It never swaps with you or crosses protected doors.',
        'The target is two to three cells away and still has a visible, walkable side cell at resolution; occupying the side cells or opening the distance makes it miss.'),
    'seam_bind': (
        '影子被缝住一角，下一步多耗时半回合；你仍能攻击、使用道具和展开构想。',
        '它看得见目标，目标身上还没有缝影。',
        'A corner of the shadow is stitched down. The next step takes half a round longer; attacks, items and constructs remain available.',
        'It can see a target that has no Shadow Stitch.'),
    'vine_grow': (
        '根丝从盆沿伸出，至多铺三格。走过时每步多耗时零点二回合；根丝可以烧掉，也会自行消失。',
        '附近有不受保护的空地，它先前长出的根丝已全部消失。',
        'Roots spread from the pot across at most three cells. Crossing them adds 0.2 rounds per step; they can burn and eventually vanish.',
        'There is unprotected open ground, and all roots it previously grew have vanished.'),
    'mislabel': (
        '标签贴错了，视野少一格，但不会小于三格；落点预警、坐标和数值仍看得见。',
        '它看得见目标，目标还没有失焦。',
        'A misplaced label reduces vision by one cell, to a minimum of three. Warnings, coordinates and values remain visible.',
        'It can see a target that has no Blur.'),
    'echo_dash': (
        '它沿预先亮出的线向前抄走至多两格，撞到第一个目标便停，只造成一次创伤。',
        '目标在两至三格外，前进的线路可以通过。',
        'It copies at most two steps along the marked line, stopping at the first target and dealing trauma once.',
        'The target is two to three cells away, along a traversable line.'),
    'slow_pool': (
        '迟帧的光斑拖住脚步：场内每步多耗时零点二回合，离开就解除；与迟拍不叠加。',
        '它看得见落点，那里没有它留下的旧光斑。',
        'A patch of slow light adds 0.2 rounds to steps inside it. Leaving ends the effect; it does not stack with Late Beat.',
        'It can see the landing point, with no old slow-light field of its own there.'),
    'return_charge': (
        '它沿直线冲出至多三格，只伤到第一个相交的目标；冲完后停一回合才恢复行动。',
        '目标在两至四格外，冲刺路径可以通过。',
        'It charges up to three cells in a straight line, hurting only the first target crossed, then recovers for one round.',
        'The target is two to four cells away, along a traversable charge path.'),
    'mind_bite': (
        '细线咬住念头，造成一次心智创伤；命中不会替它恢复想象力。',
        '它看得见两至四格外的目标。',
        'A fine line bites into thought, dealing mind trauma once. The hit does not restore its imagination.',
        'It can see a target two to four cells away.'),
    'shadow_step': (
        '它卸去脚步的重量，移动耗时少零点二回合，最低零点八；仍看得见它，攻击也没有加快。',
        '它已经察觉目标，目标至少在三格外，而它还没有轻步。',
        'It sheds the weight of its steps, moving 0.2 rounds faster, to a minimum of 0.8. It stays visible and attacks no faster.',
        'It is alerted to a target at least three cells away and has no Light Step.'),
    'ink_pool': (
        '墨迹铺开至多五格，每步多耗时零点二回合。墨会退去，不附着在身上，也不持续损耗意识。',
        '它看得见落点，那里不是任务地形，也没有它留下的旧墨迹。',
        'Ink spreads over at most five cells, adding 0.2 rounds per step. It fades without attaching to bodies or causing ongoing resource loss.',
        'It can see a non-quest landing point with no old ink field of its own.'),
    'lullaby': (
        '断续歌声带来倦意，下一步多耗时半回合；不会强迫你等待、沉眠，也不妨碍使用道具。',
        '它看得见目标；目标没有倦意，并已度过上次控制后的保护间隔。',
        'The broken song brings drowsiness, adding half a round to the next step. It forces neither waiting nor sleep and leaves items usable.',
        'It can see a target without Drowsiness whose protection after the last control effect has ended.'),
    'wake_allies': (
        '牧杖指过的同伴，移动耗时少零点二回合，最低零点八；伤害和攻击速度照常，重复指引不会越走越快。',
        '至少一名同伴正在追踪你，还没有得到引路。',
        'Guided allies move 0.2 rounds faster, to a minimum of 0.8. Damage and attack speed stay unchanged; repeated guidance does not compound.',
        'At least one ally is tracking you and has no Guidance.'),
    'fire_seed': (
        '歌声点起三格火，持续两回合。每回合造成一点清醒或完整度创伤；有水和防火的地面不会起火。',
        '它看得见可点火的落点，先前唱出的火场已经熄灭。',
        'The song lights three cells for two rounds, dealing one lucidity or integrity trauma per round. Water and fireproof ground cannot ignite.',
        'It can see an ignitable landing point, and its previous fire field has ended.'),
    'electric_stitch': (
        '电针先击一次，再沿两格内的导电材料传开，至多六格。余电每回合一点，共两次；电痉挛只拖慢一回合的脚步零点三回合，仍能攻击。',
        '导电落点可见；水或导电液至少八单位，或地面是金属，且至少有一条安全退路。',
        'The needle strikes once, then conducts within two cells across at most six cells. Residual current deals one per round twice; Electric Spasm adds 0.3 rounds to movement for one round, without blocking attacks.',
        'The visible landing point has metal or at least eight units of water or conductive liquid, with a safe way out.'),
    'gift_bomb': (
        '礼盒在预先亮出的固定位置炸开，只按这次爆破造成一份创伤，并把目标推开一格。',
        '落点在两至五格外且可见，它前一枚礼盒已不在场。',
        'The gift bursts at the marked fixed point, dealing its explosion trauma once and pushing targets one cell.',
        'The visible landing point is two to five cells away, with no earlier gift of its own still present.'),
    'fog_veil': (
        '它吐出一口薄雾，遮断穿过雾格的远程视线；贴身仍可攻击，雾也不会留下附着创伤。',
        '落点能遮住至少一条敌我远程线路，但不会堵住唯一出口。',
        'A breath of mist blocks ranged sight through its cells. Adjacent attacks remain possible, and the mist leaves no attached trauma.',
        'The mist can cross at least one ranged line without blocking the only exit.'),
    'edit_heal': (
        '它修回两点完整度。一次遭遇中，普通和强烈异象至多修回初始完整度的两成，核心至多一成；零头舍去。',
        '受修订者完整度不高于一半，且这次遭遇还能继续修复。',
        'It restores two integrity. Per encounter, ordinary and strong anomalies can restore at most 20% of initial maximum integrity, cores 10%, rounded down.',
        'The recipient has at most half integrity and has not used all its healing for this encounter.'),
    'space_fold': (
        '房间折起至多两格薄面，每面完整度二，可以击破。它们挡住弹道，却能走过；过一段时间便展平。',
        '那里是不受保护的地形，它先前留下的折面已经展平。',
        'The room raises at most two folds, each with two integrity and breakable. They block shots but allow walking, then flatten when their time ends.',
        'The terrain is unprotected, and its previous folds have flattened.'),
    'split_echo': (
        '它分出一只残影：完整度二，每击一点、耗时两回合，四回合后消失。残影没有技能，也不掉落物品；一次只留一只。',
        '可见的空位能容下残影，它先前的残影已消失。',
        'It makes one echo with two integrity, one trauma per two-round attack, lasting four rounds. The echo has no skills or drops; only one can remain.',
        'A visible empty cell can hold it, and its previous echo has vanished.'),
    'choir_guard': (
        '和声护住同伴的下一次受击，少一点创伤，最低一点。与护折只取较强的一层；已有的护幕不会重新计时。',
        '至少一名同伴还能得到护幕，尚未达到减伤限度。',
        'Harmony reduces each ally\'s next hit by one trauma, to a minimum of one. It uses the stronger of this and Fold Guard; existing harmony is not renewed.',
        'At least one ally can receive the guard and has not reached the damage-reduction limit.'),
    'stair_fracture': (
        '阶沿剥落，使一面普通墙少二十点完整度。机关墙、边界、出口与箱子不会受影响，也不会一击清掉整墙。',
        '前方有能破坏的普通墙，打通它能开出一条路线。',
        'The stair edge crumbles, removing twenty integrity from an ordinary wall. It leaves mechanisms, boundaries, exits and boxes intact and cannot clear a whole wall at once.',
        'A breakable ordinary wall can open a route.'),
    'redact_buff': (
        '它划去你的一项临时正面征兆，先找护盾，再找轻步，最后找回复；不会永久封住构想。',
        '你身上确有可划去、与任务无关的临时正面征兆。',
        'It crosses out one temporary beneficial portent, preferring shields, then Light Step, then recovery. Constructs are not permanently sealed.',
        'You have a removable temporary beneficial portent unrelated to quests.'),
    'abyss_pull': (
        '量尺收紧，把命中的目标沿亮出的方向拉近一格；不穿墙，不拖进未标出的危险，也不接着再拉。',
        '目标在两至五格外且可见，拉近后的格子可以落脚。',
        'The tape tightens, pulling a struck target one cell along the marked direction. It crosses no walls, enters no unmarked danger and pulls only once.',
        'The visible target is two to five cells away, with a legal destination.'),
    'oblivion_mark': (
        '批注的墨淡下去，每回合带走一点想象力，共两点。不会沾成材料附着，深处也不会加重，更不同时抽走心智。',
        '目标还有想象力、未带淡墨，并已度过上次控制后的保护间隔。',
        'The annotation fades, taking one imagination each round, twice. It leaves no material attachment, grows no stronger with depth and takes no mind as well.',
        'The target has imagination left, no Faded Ink, and no remaining protection from the last control effect.'),
    'nightmare_patch': (
        '缝出的梦刺每回合造成一点心智创伤，至多两次；异象在其中受一点完整度创伤。同一格重叠的场只取最强创伤。',
        '那里没有它留下的旧梦刺，也不会封住唯一安全通路。',
        'Stitched dream thorns deal one mind trauma per round, at most twice; anomalies take one integrity trauma. Overlapping fields use only the strongest cell damage.',
        'Its earlier dream thorns are absent, and the only safe passage stays open.'),
    'null_ray': (
        '空白光束沿固定直线伸出至多五格，碰到第一个实体就截断；不穿墙，也不追着移动后的目标改向。',
        '它看得见两至五格外的目标。',
        'A blank beam reaches up to five cells along a fixed line and stops at the first solid target. It neither passes walls nor turns after a moving target.',
        'It can see a target two to five cells away.'),
    'core_beacon': (
        '灯塔转出一片固定朝向的扇光，至多七格，每个目标只受击一次。转光前，扇形边缘和所有受击格都会亮出。',
        '它看得见目标，并能提前亮出所有可能受击的位置。',
        'The lighthouse turns a fixed fan of light across at most seven cells, striking each target once. Both edges and every affected cell are marked beforehand.',
        'It can see the target and mark every cell that may be struck in advance.'),
    'core_summon': (
        '执念凝出一只残影：完整度三，每击一点、耗时两回合，五回合后消失。它至多留下两只，残影没有技能、掉落或奖励。',
        '可见的空位能够落脚，它留下的残影还不到两只。',
        'The fixation makes one echo with three integrity, one trauma per two-round attack, lasting five rounds. At most two remain, with no skills, drops or rewards.',
        'A visible empty cell is suitable, and fewer than two of its echoes remain.'),
    'core_period': (
        '句末的墨压住念头，造成一次心智创伤；击中时另带走一点想象力，之后不留下淡墨或持续附着创伤。',
        '它看得见目标，目标已度过上次控制后的保护间隔。',
        'The sentence end deals mind trauma once and takes one imagination on a hit, leaving no Faded Ink or ongoing attached trauma.',
        'It can see a target whose protection after the last control effect has ended.'),
    'core_pause': (
        '句子停住了，一回合内不能移动；道具、构想和攻击仍可用。停顿结束后，四回合内受到控制保护。',
        '你尚未驻足，控制保护已结束，且这次停顿不会与强力伤害同时落下。',
        'The sentence stops movement for one world round, leaving items, constructs and attacks usable. Four rounds of control protection follow.',
        'You are not Rooted, control protection has ended, and the pause will not land with a powerful damaging skill.'),
    'core_cry': (
        '初啼传进两格内可见、相通的声路，只波及这片范围，并告知至多两名同伴你的位置。',
        '它看得见目标，声音能传到，受击范围外还留着退路。',
        'The first cry reaches visible, connected sound paths within two cells, affecting only that area and alerting at most two allies to your position.',
        'It can see a target along a sound path, with a route out of the affected cells.'),
    'core_chill': (
        '冻嚎留下三格寒痕，敌我经过时每步多耗时零点三回合。不会冻住、催眠，也不持续损耗意识。',
        '它看得见目标，先前的寒痕已消失，也不会与驻足重叠。',
        'The frozen howl leaves three frost cells, adding 0.3 rounds to steps for either side. It does not freeze, cause sleep or drain resources over time.',
        'It can see the target, its previous frost field has ended, and this will not overlap Rooted.'),
    'scribe_stroke': (
        '笔锋沿固定直线划过，最长六格，只打中第一个实体。无论战斗到了哪一阶段，落笔前都亮出这条线。',
        '执笔者正在战斗，且看得见目标。',
        'The pen cuts a fixed line up to six cells long, striking only the first solid target. Every battle phase marks the line before the stroke.',
        'The Scribe is in battle and can see the target.'),
    'scribe_draft': (
        '草稿在菱形范围里击打一次，命中后使目标失焦两回合；不留下残影或额外持续创伤。',
        '执笔者正在战斗，影响范围外至少留着一条安全退路。',
        'The draft strikes once in a diamond and blurs struck targets for two rounds, without leaving echoes or additional ongoing trauma.',
        'The Scribe is in battle, with at least one safe route outside the affected area.'),
    'scribe_erase': (
        '橡皮擦去至多五格临时敌方效果场，另可让一格普通墙少二十点完整度。事件、出口、掉落和你的构想仍留着。',
        '范围里有可擦掉的临时场，或一格可破坏的普通墙。',
        'The eraser clears at most five cells of temporary hostile fields and can remove twenty integrity from one ordinary wall. Events, exits, drops and your constructs remain.',
        'The area contains a removable temporary field or a breakable ordinary wall.'),
    'scribe_revision': (
        '它擦去自己的一项负面征兆，也擦去你的一项非任务负面征兆，并补一点想象力；不改完整度。每个战斗阶段只校订一次。',
        '新的战斗阶段尚未校订过，且它或你身上有可清洗的征兆。',
        'It removes one harmful portent from itself and one non-quest harmful portent from you, adding one imagination without changing integrity. It revises once per battle phase.',
        'The new battle phase has not been revised, and either of you has a washable portent.'),
}

EN_SKILL_PROSE = {
    zh: en
    for effect, condition, effect_en, condition_en in SKILL_PROSE.values()
    for zh, en in ((effect, effect_en), (condition, condition_en))
}
