"""异象视觉／听觉显式配置（docs 261022 §7）。

目录内 93 项全部显式审核：91 项有 V/H/T，2 项非普通视听单位登记在
``NON_PERCEPTION``。数值是首轮试验值；普通型 V 8—12、H 6—8，低视距
听觉特化与埋伏型按角色单独压／抬，不把批量默认值当成机制完成。

- ``vision``：基础视距 V；为空表示沿用定义表。
- ``hearing``：听觉上限 H（曼哈顿格）；``None`` 表示旧声圈行为。
- ``threshold``：接收阈值 T（声强单位）；越高越难被弱声惊动。
- ``note``：该角色为何偏离普通基准——审核记录，不是界面文案。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PerceptionProfile:
    vision: int | None = None
    hearing: int | None = None
    threshold: int = 0
    note: str = ""


PROFILES: dict[str, PerceptionProfile] = {
    # 基准／普通
    "anomaly.page_hound": PerceptionProfile(6, 10, -2, "近视耳灵"),
    "anomaly.folded_person": PerceptionProfile(10, 7, 0, "视觉远于声音的基准"),
    "anomaly.paper_fish": PerceptionProfile(6, 6, 0, "感知较短，保留亲液"),
    "anomaly.human_coat_rack": PerceptionProfile(7, 6, 1, "埋伏、短听"),
    "anomaly.model_porter": PerceptionProfile(9, 5, 2, "可远望、耳迟钝"),
    # 视觉特化
    "anomaly.backlit_reader": PerceptionProfile(13, 6, 1, "视觉特化"),
    "anomaly.long_take_director": PerceptionProfile(16, 6, 2, "远视、易被遮挡"),
    "anomaly.mirror_attendant": PerceptionProfile(12, 5, 2, "视觉型、弱诱饵不响"),
    "anomaly.silent_audience": PerceptionProfile(12, 5, 2, "远视耳迟钝"),
    "hospital.scan_halo": PerceptionProfile(14, 5, 2, "视觉特化"),
    "library.lamp": PerceptionProfile(12, 6, 1, "借光远视"),
    # 听觉特化／敏锐
    "anomaly.reverse_drummer": PerceptionProfile(8, 10, -2, "普通听觉敏锐"),
    "anomaly.echo_door": PerceptionProfile(6, 12, -2, "听觉特化"),
    "anomaly.insomniac_alarm": PerceptionProfile(5, 9, -2, "小视野、易惊醒"),
    "hospital.listener": PerceptionProfile(5, 12, -3, "听觉特化"),
    # 双感官／追猎
    "anomaly.clock_keeper": PerceptionProfile(11, 8, 0, "双感官"),
    "anomaly.fog_breather": PerceptionProfile(7, 9, -1, "自己的雾阻视、不阻声"),
    "anomaly.wet_choir": PerceptionProfile(10, 11, -1, "听觉较宽"),
    "anomaly.sleepless_watch": PerceptionProfile(13, 9, 0, "双感官追猎"),
    "library.reader": PerceptionProfile(10, 7, 0, "位面基准"),

    # ---- 常规异象：角色分工审核（2026-10-22）----
    # 埋伏／伪装：视距落在普通区间下限，听觉不高，靠贴近触发。
    "anomaly.ink_archivist": PerceptionProfile(6, 6, 2, "静止伪装成档案，靠贴近显形"),
    "anomaly.floppy_collector": PerceptionProfile(6, 6, 1, "伪装收集者，短视短听"),
    "anomaly.door_mimic": PerceptionProfile(5, 6, 1, "拟门埋伏，只认靠近的钥匙"),
    "anomaly.faceless_watchman": PerceptionProfile(7, 6, 1, "守夜人靠更次而非听觉"),
    # 追猎／压迫：视觉偏高，但不会全图锁定。
    "anomaly.cursor_hunter": PerceptionProfile(10, 6, 1, "指针型追猎，视线明确"),
    "anomaly.primordial_impulse": PerceptionProfile(7, 6, -1, "不知停顿的直线冲动，感知短"),
    "anomaly.null_witness": PerceptionProfile(8, 5, 2, "存在性注视，不靠声音"),
    "anomaly.door_warden": PerceptionProfile(9, 8, 0, "守门人记住锁孔与敲门声"),
    "anomaly.silent_mirror": PerceptionProfile(7, 6, 1, "复制脚步、不主动循声，只在被刻意惊动时回应"),
    "anomaly.return_runner": PerceptionProfile(6, 7, 0, "往返跑者，路线固定"),
    "anomaly.rewind_ghost": PerceptionProfile(7, 6, 0, "倒带路线，感知按录像范围"),
    "anomaly.deadlink_roamer": PerceptionProfile(6, 7, 0, "断链漫游，普通视听"),
    "anomaly.sleepwalking_tailor": PerceptionProfile(7, 7, 0, "贴身处剪口袋，短距视听"),
    "anomaly.potted_keeper": PerceptionProfile(7, 7, 0, "躲在长高草里，不靠远听"),
    "anomaly.tamper_omission": PerceptionProfile(8, 7, 0, "脚步缺一拍的近身者"),
    "anomaly.thought_worm": PerceptionProfile(6, 7, 0, "近身咬念，听觉普通"),
    "anomaly.dream_accountant": PerceptionProfile(7, 7, 0, "记账型，视野普通"),
    "anomaly.ticket_inspector": PerceptionProfile(6, 7, 0, "只看票面，不追声音"),
    "anomaly.static_viewer": PerceptionProfile(6, 7, 1, "守着无信号屏幕，反应迟钝"),
    "anomaly.screensaver_bubble": PerceptionProfile(4, 6, 2, "飘浮屏保，几乎不感知"),
    "anomaly.slow_projector": PerceptionProfile(5, 6, 2, "慢半拍，视听都短"),
    "anomaly.ink_bottle_guard": PerceptionProfile(6, 7, 0, "守瓶，靠墨迹范围"),
    "anomaly.unopened_gift": PerceptionProfile(6, 7, 1, "投掷型，短视短听"),
    "anomaly.cooling_doll": PerceptionProfile(8, 7, 0, "动作缓慢但从不迟到的跟踪者"),
    "anomaly.pager_sprite": PerceptionProfile(7, 9, -1, "传呼机噪声让它听觉较灵"),
    "anomaly.disco_echo": PerceptionProfile(7, 9, -1, "舞会残响形成宽声场"),
    "anomaly.subtitle_group": PerceptionProfile(7, 8, 0, "给全梦配字幕，听觉稍宽"),
    "anomaly.popup_peddler": PerceptionProfile(6, 7, 0, "噪音型推销，不以视听见长"),
    "anomaly.stair_echo": PerceptionProfile(6, 8, 0, "固定楼梯巡逻，循回声"),
    "anomaly.sunken_bell": PerceptionProfile(7, 9, -1, "钟声震出涟漪"),
    "anomaly.lullaby_hummer": PerceptionProfile(6, 9, -1, "歌声传播广于视觉"),
    "anomaly.pyre_singer": PerceptionProfile(7, 9, -1, "高音引火，声音先到"),
    "anomaly.echo_scribe": PerceptionProfile(7, 9, -1, "连急躁一起抄，听觉较灵"),
    "anomaly.oblivion_archivist": PerceptionProfile(7, 6, 1, "归档靠触碰名字"),
    "anomaly.forgetter": PerceptionProfile(9, 6, 1, "拆名字的线，视觉型"),
    # 群体／强烈：数量或范围带来压力，单体仍可绕开。
    "anomaly.double_exposure": PerceptionProfile(9, 7, 0, "分裂体共享普通视听"),
    "anomaly.projection_crew": PerceptionProfile(9, 7, 0, "巡回放映，镜头方向为主"),
    "anomaly.whole_choir": PerceptionProfile(8, 10, -1, "多声部叠加，听觉较宽"),
    "anomaly.startup_chorus": PerceptionProfile(7, 11, -2, "开机音合唱，宽声场"),
    "anomaly.nightmare_weaver": PerceptionProfile(9, 7, 1, "编织记忆，视觉型"),
    "anomaly.nightmare_herder": PerceptionProfile(9, 7, 1, "牧群首领，视觉型"),
    "anomaly.bsod_warden": PerceptionProfile(8, 6, 1, "守着死屏，视线固定"),
    "anomaly.silent_proofreader": PerceptionProfile(8, 6, 1, "涂黑型，近身才准"),
    "anomaly.abyss_ruler": PerceptionProfile(7, 6, 0, "量尺伸得远，本体感知普通"),
    "anomaly.folded_room": PerceptionProfile(10, 6, 2, "空间折叠，听觉被结构隔断"),
    "anomaly.faceless_editor": PerceptionProfile(10, 7, 1, "删改边界，视觉型"),
    # 核心执念：独特感知另算；普通视听按主题给，不因是首领就全图锁定。
    "anomaly.unfinished_period": PerceptionProfile(10, 6, 1, "未完成句的收束，视觉型"),
    "anomaly.hollow_lighthouse": PerceptionProfile(9, 9, 0, "照彻是独特能力，普通听觉另计"),
    "anomaly.first_cry": PerceptionProfile(10, 10, -2, "啼哭前的寂静，听觉宽"),
    "anomaly.scribe": PerceptionProfile(9, 6, 1, "按键声细密，本体视力普通"),
    "anomaly.core_y2k_worm": PerceptionProfile(9, 8, 0, "停在世纪末，双感官普通"),
    "library.core": PerceptionProfile(9, 8, 0, "目录记录一切，听觉稍宽"),

    # ---- 医院：器械型，多数没有耳朵，靠动作范围 ----
    "hospital.membrane": PerceptionProfile(6, 6, 1, "触碰即缩回，短距感知"),
    "hospital.capsid": PerceptionProfile(7, 5, 2, "射针器械，听觉差"),
    "hospital.sporebud": PerceptionProfile(4, 5, 2, "静止孢芽，几乎不主动感知"),
    "hospital.filament": PerceptionProfile(5, 6, 1, "沿接缝铺展，感知低"),
    "hospital.syringe": PerceptionProfile(7, 6, 1, "游走注射器，针尖先转向"),
    "hospital.forceps": PerceptionProfile(6, 6, 1, "空中开合，短距"),
    "hospital.dripstand": PerceptionProfile(5, 5, 2, "推着输液架，感知低"),
    "hospital.spore_crown": PerceptionProfile(9, 5, 2, "培养皿圆冠，视觉高、听觉差"),
    "hospital.blade_disc": PerceptionProfile(8, 6, 1, "刀片转盘，视线随旋转"),
    "hospital.core_sterile_grace": PerceptionProfile(9, 6, 2, "相信清除变化即安全，听觉低"),

    # ---- 图书馆：阅读／抄写型，视觉与听觉分开 ----
    "library.threshold": PerceptionProfile(6, 7, 0, "门前迟疑，普通视听"),
    "library.page": PerceptionProfile(5, 6, 1, "倒写页码，感知短"),
    "library.narrator": PerceptionProfile(6, 8, 0, "旁白靠声音，听觉稍宽"),
    "library.index": PerceptionProfile(7, 8, 0, "索引追页，听觉稍宽"),
    "library.foldwalker": PerceptionProfile(6, 7, 0, "折页行者，普通视听"),
    "library.binder": PerceptionProfile(6, 6, 1, "收散页，短听"),
    "library.scribe": PerceptionProfile(8, 7, 1, "抄写一切，视觉略高"),
    "library.witness": PerceptionProfile(9, 7, 0, "多版本见证，视觉型"),
    "library.refuser": PerceptionProfile(8, 6, 1, "拒绝誊清，短听"),
}


def perception_profile(catalog_id: str) -> PerceptionProfile | None:
    return PROFILES.get(catalog_id)


# 非普通视听单位：迁徙楼梯／空白裂隙不转成听声追人单位。
NON_PERCEPTION = frozenset({"anomaly.moving_staircase", "anomaly.blank_rift"})

# 听界：持续回合与起手声径（docs 261022 §16.4）。
LISTEN_REALM_TURNS = 3
LISTEN_REALM_SELF_RADIUS = 3
# 循声定位：确认所需余量与标记保留回合（docs 261022 §16.4）。
CONFIRMED_SOURCE_RESIDUAL = 4
CONFIRMED_SOURCE_RETENTION = 2
