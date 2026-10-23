"""Small, forgiving realm challenges: geometry, controls and bilingual guidance."""
EMBER_STAGES = (
    {'gate': (14, 12), 'jet': (13, 12), 'source': (11, 12), 'panel': (12, 10), 'safe': (12, 11)},
    {'gate': (24, 12), 'jet': (23, 12), 'source': (21, 12), 'panel': (22, 10), 'safe': (22, 11)},
    {'gate': (33, 12), 'jet': (32, 12), 'source': (30, 12), 'panel': (31, 10), 'safe': (31, 11)},
)
EMBER_CONTAINER = (23, 13)
EBBING_REWARD_SPOTS = ((13, 18), (28, 17), (28, 7))
EBBING_GUARDS = ((12, 16), (29, 15), (27, 8))
EMBER_GUARDS = ((19, 13), (28, 13))
TEXT = {
    'repeat': ('　可重复操作', ' | Retryable'),
    'empty_exit': ('空手跨出去（行囊满也可离开）', 'Leave without the exit gift (works with a full pack)'),
    'valve0': ('蜡门前的分流闸', 'Wax-door sluice'),
    'valve1': ('蚀刻池的混液阀', 'Etching-pool mixing valve'),
    'valve2': ('热气室的冷却排压阀', 'Hot-chamber cooling and vent valve'),
    'hint0': ('接通燃油，再打开分流闸。油从高处沿凹槽流到蜡门脚下；观察终端燃油达到 20 后，在阀下绝热带点燃，等待蜡门融化。供料可重试，排空可纠错。', 'Feed oil, then open the sluice. Oil flows downhill through the channel to the wax door. Once terminal oil reaches 20, ignite from the insulated tile below the valve and wait for the wax to melt. Retry or drain after mistakes.'),
    'hint1': ('先徒手推倒下方酸罐，再接通酸液泵。酸沿凹槽蚀穿压实墙，不需要点火。兑水可增加酸液流量：水被酸同化，而非把酸变没；站在绝热带等蚀刻完成。', 'Topple the acid can below, then connect the acid pump. Acid flows through the channel and etches the compacted wall; no ignition is needed. Mixing water increases the flow because acid assimilates water. Wait on the insulated strip.'),
    'hint2': ('供气阀带热锁：先接通供料，开冷却水，让水沿凹槽扑灭终端明火，气室才会充气；再排压两回合，压力在 60–99 时从阀下点燃。水灭火、低压缩小爆炸范围；可排空重试。', 'A thermal lock holds gas back: connect feed and open cooling water. Water flows down the channel and extinguishes the terminal heater before gas enters. Vent for two rounds, then ignite below the valve at pressure 60–99. Lower pressure limits the blast. Drain to retry.'),
    'feed': ('接通供料', 'Connect feed'),
    'vent': ('打开排风', 'Open the vent'),
    'light': ('点燃终端', 'Ignite terminal'),
    'leave': ('暂时离开阀台', 'Leave the valve'),
    'need_can': ('先徒手推倒下方的酸罐，再接通导流泵。', 'Topple the acid can below before connecting its pump.'),
    'route': ('打开分流闸', 'Open the sluice'),
    'mix': ('兑水增流', 'Mix water into acid'),
    'cool': ('打开冷却水', 'Open cooling water'),
    'drain': ('排空本段供料', 'Drain this stage'),
    'routed': ('分流闸打开了，燃油开始沿凹槽下流。', 'The sluice opens; oil begins flowing downhill.'),
    'mixed': ('水兑进酸液，混合物仍是酸蚀液，流量增加。', 'Water mixes into the acid; the mixture remains acid with more volume.'),
    'cooling': ('冷却水已接通，观察终端火焰熄灭后再排压。', 'Cooling water connected. Wait for the terminal flame to go out, then vent.'),
    'drained': ('这一段的供料已排空，可以重新操作。已打开的隔墙保持开放。', 'This stage is drained and can be retried. Cleared partitions stay open.'),
    'not_ready': ('燃油还没有到达终端；打开分流闸并观察流量，不必射击墙体。', 'Oil has not reached the terminal. Open the sluice and watch the flow; shooting the wall is unnecessary.'),
    'too_hot': ('终端明火尚未冷却：先打开冷却水，等水灭火后再排压点燃。', 'The terminal is still hot. Open cooling water and wait for it to extinguish the flame before venting and igniting.'),
    'flow': ('凹槽终端 {kind} {amount} · 隔墙完整度 {integrity} · 供料 {feed}', 'Channel terminal: {kind} {amount} | Partition integrity {integrity} | Feed {feed}'),
    'chamber': ('气包压力 {pressure} · 冷却 {cooled} · 排风 {vent}', 'Pressure {pressure} | Cooled {cooled} | Vent {vent}'),
    'fed': ('供料接通了。气包压力 {pressure}；站在阀下的绝热带点火，供料会保持到隔墙打开。', 'Feed connected. Pocket pressure: {pressure}. Ignite from the insulated tile below the valve; feed lasts until the partition opens.'),
    'vented': ('排风已打开。再等 {rounds} 回合，让压力降到 100 以下。', 'Vent opened. Wait {rounds} more rounds for pressure below 100.'),
    'unprimed': ('还没有接通供料；这只阀可以反复尝试。', 'Connect the feed first; this valve can be retried.'),
    'blocked_jet': ('终端被障碍挡住或落在阻燃地面上，火种没有点燃。检查终端位置，再尝试供料和点火。', 'The terminal is blocked or on fireproof ground; it did not ignite. Check the terminal before retrying its feed and lighter.'),
    'unsafe': ('靠近阀台操作；点火时请站到阀下的绝热带。', 'Operate beside the valve; ignite from the insulated tile directly below it.'),
    'high': ('压力仍为 100：先排风并等两回合，避免近处的冲击。', 'Pressure is still 100: vent and wait two rounds to avoid the nearby shock.'),
    'lit': ('终端点燃了，观察隔墙的材料反应。', 'The terminal ignites. Watch the partition react.'),
    'cleared': ('第 {stage} 道隔墙打开，供料自动停止；可以继续过桥。', 'Partition {stage} opened; its feed stops automatically. Cross the bridge.'),
    'pressure': ('气包压力 {pressure} · 供料 {feed} · 排风 {vent}', 'Pressure {pressure} | Feed {feed} | Vent {vent}'),
    'on': ('接通', 'on'), 'off': ('关闭', 'off'),
    'full_lighter': ('行囊已满；阀旁的火种仍可直接使用，不占行囊。', 'Your inventory is full; valve lighters remain usable without an inventory slot.'),
    'ember_intro': ('三段分别用油融蜡、酸液蚀墙、水冷却后排压爆破。阀台可重复操作，射击不能破坏封签方块；上浮可暂时离开并保留进度。', 'Three stages: oil melts wax, acid etches stone, then water cools a pressure chamber before a controlled blast. Controls are retryable; bullets cannot break sealed blocks. Ascend to leave temporarily and keep progress.'),
    'tide_intro': ('门槛内可以整备或上浮；跨出去后先有 6 回合缓冲，之后每 6 回合吞一圈。近处取一件，东侧争取第二件，北侧回形针需更快路线；中心出口随时可用。', 'Prepare or ascend on the starting platform. Crossing gives 6 grace rounds, then one ring closes every 6 rounds. Take a nearby piece, try the eastern one, or hurry north for the clip. The central exit stays available.'),
    'tide_start': ('身后的门合拢；退潮将在 6 回合缓冲后开始。', 'The door closes behind you; the tide starts after 6 grace rounds.'),
    'tide_warn': ('第 {ring} 圈将在 {rounds} 回合后收缩；中心出口还剩 {remaining} 回合。', 'Ring {ring} closes in {rounds} rounds; the central exit has {remaining} rounds left.'),
    'tide_status': ('退潮 {ring}/10 · 下圈 {next} · 出口 {left}', 'Tide {ring}/10 | Next {next} | Exit {left}'),
    'ember_status': ('廊桥隔墙 {cleared}/3', 'Bridge partitions {cleared}/3'),
    # 掉线拨号（M5，2026-10-10）：主梦机制，借用 challenge_status 作状态栏通道
    # （见 core/realm_challenges.challenge_status 的拨号分支；EN 模板在 i18n_ui_en.py）。
    'dial_status': ('网络邻居敲门 · 剩 {n} 回合', 'Network neighbor knocking · {n} rounds left'),
    'tide_exit_desc': ('近袋在西南，第二袋在东侧，回形针在东北。想带走多少，由你决定；来不及就先从中心出去。失败最多扣 5 心智。', 'A nearby cache lies southwest, another east, and the clip northeast. Choose what to take; leave through the center when time is short. Failure costs at most 5 Mind.'),
    'gloves': ('焦边的手套', 'Singed Gloves'),
    'gloves_desc': ('布边被火烤卷了：爆炸冲击造成的清醒创伤减少 1，至少承受 1；不免疫火焰，也不阻止燃烧附着。', 'The fabric edges have curled: explosion shock deals 1 less Lucidity trauma, with a minimum of 1. It grants no fire immunity and does not prevent Burning.'),
    'gloves_pick': ('取走焦边的手套（爆炸冲击 −1）', 'Take Singed Gloves (shock -1)'),
    'padding': ('缓冲冲击', 'Cushion shock'),
    'padding_desc': ('爆炸冲击造成的清醒创伤最多减少 1，至少承受 1；不叠加为爆炸免疫。', 'Explosion shock deals at most 1 less Lucidity trauma, with a minimum of 1. Stacking never grants immunity.'),
    'edge_desc': ('每个留白续写件只按自己那份次级强度生效；按实际经过的回合回流，合计额外回流每回合最多 3 点。', 'Each Blank Edge piece uses its own secondary-power threshold. Regeneration follows elapsed rounds, with at most 3 extra Imagination per round in total.'),
}


def event_definitions():
    result = {}
    for index, stage in enumerate(EMBER_STAGES):
        result[f'realm_valve.ember{index}'] = {
            'event_id': f'realm_valve.ember{index}', 'name': TEXT[f'valve{index}'][0],
            'description': TEXT[f'hint{index}'][0], 'dialogue': (TEXT[f'hint{index}'][0],),
            'kind': 'compound', 'dissolution_reward': 0,
            'options': tuple({'label': TEXT[key][0], 'ember_control': {'stage': index, 'action': key}}
                             for key in (('feed', 'route', 'light', 'drain') if index == 0 else
                                         ('feed', 'mix', 'drain') if index == 1 else
                                         ('feed', 'cool', 'vent', 'light', 'drain')))
                       + ({'label': TEXT['leave'][0], 'leave': True},),
        }
    # ---- 梦中梦·千禧园（2026-10-10）：零点体育场中央终端 ----
    # 选项 "summon_y2k"：接入 → 敌对千年虫登场（core/actions.choose_event_option
    # 的专属分支结算，见 docs/millennium-garden-design.md §10.3 路径 A）。
    result['event.millennium_terminal'] = {
        'event_id': 'event.millennium_terminal', 'name': '蓝屏终端',
        'description': '一台发着蓝光的终端立在体育场中央，屏幕上的进度条停在 99%。',
        'kind': 'compound', 'dissolution_reward': 0,
        'dialogue': (
            '屏幕上的字一闪一闪：你的电脑遇到问题，需要重新启动。',
            '光标在闪。光标后面有一行小字：按任意键接入……',
        ),
        'options': (
            {'label': '接入', 'summon_y2k': True},
            {'label': '不去动它', 'leave': True},
        ),
    }
    return result
