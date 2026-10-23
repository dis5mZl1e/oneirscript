"""English vocabulary for the authored clinical and literary realms."""
EN_REALMS = {
'至白疗所':'The White Sanctuary','未尽藏书宫':'Palace of Unfinished Books',
'接引的白厅':'White Reception Hall','配液工坊':'Mixing Workshop','气相静室':'Quiet Gas Chambers','白昼病房':'Daylight Wards','无垢圣所':'Immaculate Sanctum',
'不闭合的手术剪':'Unclosed Surgical Shears','停痛糖衣':'Pain-Coated Sweet','免疫球蛋白锭':'Immunoglobulin Lozenge','净气小瓶':'Clean-Air Vial','口服的清晨':'Oral Morning','失时索引':'Index of Lost Time','封口安瓿':'Sealed Ampoule','心搏标签':'Pulse Tag','拒誊羽笔':'Quill of Refusal','无垢手套':'Immaculate Glove','无菌咀嚼片':'Sterile Chew','晨醒含片':'Morning-Wake Lozenge','梦敏颗粒':'Dream-Sensitive Granules','洗忆泡腾片':'Memory-Wash Effervescent Tablet','淋巴滤环':'Lymph Filter Ring','淋巴素软胶囊':'Lymph Capsule','滤膜囊':'Filter-Membrane Pouch','玻璃肋':'Glass Rib','甘眠露':'Gentle-Sleep Dew','生理盐片':'Saline Tablet','缓释凝片':'Slow-Release Gel Tablet','留白纸镇':'Blank-Space Paperweight','白昼面罩':'Daylight Mask','白瓷维生素':'Porcelain Vitamin','空心针':'Hollow Lancet','缝合线圈':'Suture Coil','罗生门残页':'Rashomon Fragment','脑脊安瓿':'Cerebral Ampoule','脑脊滴':'Cerebral Drops','蝶梦借阅证':'Butterfly-Dream Library Card','诊断玻片':'Diagnostic Slide','载氧棉糖':'Oxygen-Cotton Candy','退烧的雪':'Fever-Cooling Snow','门前书签':'Doorstep Bookmark','阿莱夫透镜':'Aleph Lens','隐城折页':'Invisible-City Fold','骨髓糖':'Marrow Sweet','骨髓银匙':'Silver Marrow Spoon',
'胡桃木书架':'Walnut Bookshelf','推书车':'Book Cart','防火书柱':'Fireproof Book Pillar','黄铜阅读灯':'Brass Reading Lamp',
'嵌壁梦灯':'Niche Dream Lamp','弧光灯架':'Arc Lamp Rig','余烬灯盏':'Ember Lamp',
'倒写的页码':'Reversed Page Number','借光的校对者':'Proofreader Borrowing Light','多版本见证':'Witness of Many Versions','折页行者':'Folded-Page Walker','拒绝誊清者':'One Who Refuses the Fair Copy','擦去的旁白':'Erased Narration','散页装订者':'Binder of Loose Leaves','无人称抄写员':'Impersonal Scribe','未借出的读者':'Unborrowed Reader','未尽目录':'Unfinished Catalogue','迟到的索引':'Belated Index','门前迟疑者':'Hesitant Reader at the Door',
'胞尘附着':'Spore-Dust Attachment','薄湿':'Light Dampness','晨视':'Morning Sight','醚迟':'Ether Slowness','胶迟':'Gel Slowness','银盐显形':'Silver-Salt Revelation','轮廓显形':'Outline Revealed','借阅视窗':'Borrowed View','停痛':'Pain Buffer','免疫球':'Immune Buffer','梦敏':'Dream Sensitivity','淋巴素':'Lymph Boost','缓释':'Slow Release','载氧':'Oxygen Carrying',
'恢复心智14，不增加上限。':'Restores 14 Mind without increasing its maximum.',
'恢复清醒14，不增加上限。':'Restores 14 Lucidity without increasing its maximum.',
'恢复想象12，不增加上限。':'Restores 12 Imagination without increasing its maximum.',
'恢复心智8、清醒6，按当前缺口结算。':'Restores up to 8 Mind and 6 Lucidity, limited by current deficits.',
'4回合内不追加胞尘族伤害；不抵挡其他毒气、火焰或敌人创伤。':'Prevents added spore-dust damage for 4 rounds; other gases, fire and enemy trauma still apply.',
'6回合内下一次实际恢复后，另一种当前缺损资源补3，触发一次；派生恢复不触发。':'For 6 rounds, the next actual recovery restores up to 3 of another depleted resource once. Derived recovery cannot trigger it.',
'6回合内下一次直接命中病原体附加2点完整度创伤；非病原体不消耗。':'For 6 rounds, your next direct hit on a pathogen deals 2 extra Integrity trauma once. Other targets do not consume it.',
'6回合内下一项新负面征兆初始持续减2，至少1回合；不减免后续续效。':'For 6 rounds, shorten the initial duration of the next new negative omen by 2, to at least 1 round. Later renewals are unaffected.',
'6回合内抵扣下一次实际创伤1点，使用间隔8回合。':'Within 6 rounds, reduce the next actual trauma by 1 once. Shared interval: 8 rounds.',
'6回合内抵扣首次心智创伤2点，不减免清醒创伤。':'Within 6 rounds, reduce the first Mind trauma by 2 once. Lucidity trauma is unaffected.',
'削短一项沉眠族征兆4回合，先处理附着；无目标不消耗。':'Shorten one sleep-family omen by 4 rounds, attachment first. No valid target means no consumption.',
'削短一项热或燃烧征兆4回合；不熄灭地图火焰，无目标不消耗。':'Shorten one heat or burning omen by 4 rounds. Does not extinguish map fires; no target means no consumption.',
'没有可见敌对目标且不在危险格时恢复心智10、想象6；条件不满足不消耗。':'When no hostile target is visible and your cell is safe, restore up to 10 Mind and 6 Imagination. Otherwise nothing is consumed.',
'自然想象恢复×1.25，持续6回合；与脑脊液取最大，不加速技能。':'Natural Imagination recovery is multiplied by 1.25 for 6 rounds; take the maximum with cerebral fluid. Skills do not speed up.',
'选择一项可洗征兆削短4回合，先处理附着。取消不消耗。':'Choose one washable omen to shorten by 4 rounds, attachment first. Cancelling consumes nothing.',
'选择一项正面可洗征兆削短3回合，恢复清醒4。不足3回合不能转化。':'Shorten a chosen positive washable omen by 3 rounds to restore up to 4 Lucidity. Requires at least 3 removable rounds.',
'有限真实储量；可携带回主梦使用。':'Finite physical contents; can be carried back to the main dream and used there.',
'最多装载6单位一种液体，注入真实消耗。':'Holds up to 6 units of one liquid; injection consumes actual contents.',
'跨门后，下一次攻击小幅修正；六行动一次。':'After crossing a doorway, slightly improve your next attack. At most once every 6 actions.',
'已遇见目标的一次弱点提示；不会揭示全图。':'One weakness hint for an encountered target; does not reveal the entire map.',
'辨认相邻房间的合法连接，不穿墙。':'Identify a legal connection between adjacent rooms; never pass through walls.',
'附近无敌人时改善一次自然恢复，保留总恢复上限。':'Improve one natural recovery while no enemy is nearby, respecting the total recovery cap.',
'同一动作的观察结果汇聚，范围至多一格，不复制全额伤害。':'Combine observations from the same action within at most one cell; never duplicate full damage.',
'抵消一次弱控制，十行动一次；不抵消核心直接伤害。':'Cancel one weak control effect at most once every 10 actions; does not cancel direct core trauma.',
'真实状态变化后的短时观察收益。':'A brief observation benefit after an actual state change.',
'下一次锁定提供一个合法替代位置的信息。':'The next lock-on reveals one legal alternative position.',
'每3世界回合心智创伤1；同族不叠加。':'Deals 1 Mind trauma every 3 world rounds; effects in this family do not stack.',
'湿润条件，不恢复资源。':'Counts as dampness; restores no resources.',
'视距+1，不产生免费行动。':'Sight range +1; grants no free actions.',
'轻迟滞，移步额外0.15；与梦醚气取最大。':'Mild slowing adds 0.15 to movement time; take the maximum with dream-ether gas.',
'轻迟滞，移步额外0.15；与梦醚液取最大。':'Mild slowing adds 0.15 to movement time; take the maximum with dream-ether liquid.',
'移步额外0.15，服从软控制总上限。':'Adds 0.15 to movement time, respecting the shared soft-control cap.',
'视线内短时隐匿显形，不显示视野外目标。':'Briefly reveals concealment within line of sight; does not show targets outside sight.',
'短时诊断标记，仅正常视线内识别伪装。':'Brief diagnostic marking identifies disguises only within normal line of sight.',
'下一次实际创伤抵扣1点，触发一次即结束。':'Reduces the next actual trauma by 1, then expires.',
'首次心智创伤抵扣2点，不减免清醒创伤。':'Reduces the first Mind trauma by 2; Lucidity trauma is unaffected.',
'下一次直接命中病原体附加2点创伤，触发一次。':'The next direct hit on a pathogen deals 2 extra trauma once.',
'下一项新负面征兆初始持续减2，至少1回合。':'Reduces the initial duration of the next new negative omen by 2, to at least 1 round.',
'不追加胞尘族伤害，不减免其他来源。':'Prevents added spore-dust damage; other sources are unaffected.',
'下一次实际恢复后另一种缺损资源补3；只触发一次。':'After the next actual recovery, restores up to 3 of another depleted resource once.',
'自然想象恢复×1.25，与脑脊液取最大。':'Natural Imagination recovery ×1.25; take the maximum with cerebral fluid.',
'真实接触变化后视野+1，持续3回合；同族取最大。':'After an actual contact change, sight range +1 for 3 rounds; take the maximum within this family.',
'取消':'Cancel','此设备不在当前疗所。':'This device is not in the current sanctuary.','请先接近设备。':'Approach the device first.','储罐记录不存在。':'No record exists for this tank.','没有这个设备操作。':'This device has no such operation.',
'这里有可见敌对目标或环境危险，未消耗甘眠露。':'A hostile target is visible or the environment is unsafe. Gentle-Sleep Dew was not consumed.',
'没有可处理的对应征兆，未消耗药物。':'No matching omen can be treated. The medicine was not consumed.',
'缓释仍在生效或尚未达到8回合间隔，未消耗药物。':'Slow release is still active or its 8-round interval has not elapsed. The medicine was not consumed.',
'目标位置被挡住，无法推动。':'The destination is blocked; it cannot be pushed.',
'选择滤膜囊的落点，取消不消耗。':'Choose where to throw the filter pouch; cancelling consumes nothing.',
'选择处理的征兆，取消不消耗。':'Choose an omen to treat; cancelling consumes nothing.',
'没有满足条件的可洗征兆，未消耗药物。':'No washable omen meets the requirements. The medicine was not consumed.',
'这不是药物选择。':'This is not a medicine selection.','这份药物已不在行囊中，未结算。':'This medicine is no longer in your bag; nothing was settled.',
'药物类型已改变，未结算。':'The medicine type changed; nothing was settled.','征兆已不满足条件，未消耗药物。':'The omen no longer meets the requirements; no medicine was consumed.',
'{name}：附着{a}＋持续{t} → 削短{n}回合':'{name}: attachment {a} + duration {t} → shorten by {n} rounds',
'{item}：{material} ×{n}':'{item}: {material} ×{n}','装载空心针':'Load Hollow Lancet','选择真实液体容器；取消不消耗。':'Choose a container holding actual liquid; cancelling consumes nothing.',
'封口安瓿碎开，释放了真实样本。':'The sealed ampoule breaks, releasing its actual sample.',
'剪除':'Sever','注入':'Inject','缝合':'Suture','滤过':'Filter','流畅':'Fluent','清洗':'Wash','支撑':'Support','呼应':'Respond','摄入后':'After ingestion','照见':'Reveal','施法后':'After casting','受击后':'After being hit','已照亮':'Already lit','在光中':'In light',
}

EN_REALMS.update({
    '藏书宫外墙': 'Outer Wall of the Unfinished Library',
    '书库内墙': 'Archive Partition Wall',
    '玻璃书障': 'Glass Book Screen',
    '湿墨': 'Wet Ink',
    '稀墨': 'Diluted Ink',
    '书脊胶': 'Bookbinder’s Glue',
    '书页迟滞': 'Page Drag',
    '墨痕迟滞': 'Ink Drag',
    '胶痕迟滞': 'Glue Drag',
    '胶迟滞': 'Glue Drag',
    '导电': 'Conductive',
    '湿墨拖住鞋底：移动额外耗时 +0.15，短时生效。': 'Wet ink clings to the sole, briefly adding 0.15 movement time.',
    '书脊胶短暂粘住鞋底：移动额外耗时 +0.15，持续2回合。': 'Bookbinder glue briefly clings to the sole, adding 0.15 movement time for 2 rounds.',
    '纸尘': 'Paper Dust',
    '墨雾': 'Ink Mist',
    '深胡桃木色的宫墙，厚重得像一册合拢的巨书，无法破坏。': 'A deep walnut palace wall, as immovable as a closed giant book.',
    '夹着旧纸纤维的硬墙，把一间书库与另一间隔开。': 'A hard wall threaded with old paper fibers, dividing one archive from the next.',
    '清透的隔屏，能看见屏后书架，却不能穿行。': 'A clear screen: shelves remain visible through it, but no one can pass.',
    '潮湿的墨迹沿地面缓缓摊开；久置后会散成一缕遮眼的墨雾。': 'Wet ink slowly spreads across the floor and eventually evaporates into a veil of ink mist.',
    '潮湿的墨迹沿地面缓缓摊开，厚处略微黏脚；久置后会散成一缕遮眼的墨雾。': 'Wet ink slowly spreads; thick pools slightly drag at the feet and eventually evaporate into a veil of ink mist.',
    '淡金色的装帧胶几乎不流动，踩过时移动耗时短暂增加。': 'Pale-gold binding glue barely flows and briefly slows anyone crossing it.',
    '翻页时扬起的细尘，薄薄一层，远处的书架在雾里发虚。': 'Fine dust stirred by turning pages softens the outline of distant shelves.',
    '清水冲开湿墨后留下的浅色墨水。攒到八单位，电流可以沿相连的墨迹传过去。': 'Pale ink left after water dilutes wet ink. At eight units, an electric field can travel through connected pools.',
    '湿墨蒸出的暗色雾气，吞掉几分视线，散去后只剩纸页气味。': 'Dark vapor from wet ink dims the view; when it clears, only the scent of paper remains.',
    '交付{item} ×{n}': 'Delivered {item} x{n}',
    '这一条你已经在册子上记过了。': 'You have already recorded this clue.',
    '你把这一条记在了心里。': 'You commit this clue to memory.',
    '还差：{req}（{have}/{need}）——备好了当面点收。': 'Still needed: {req} ({have}/{need}); bring it back for inspection.',
    '还差：在{name}把线索一条条查清（{have}/{need}）。': 'Still needed: check the clues at {name} ({have}/{need}).',
    '还差：{req}。': 'Still needed: {req}.',
 '膜泡球':'Membrane Orb','衣壳针':'Capsid Needle','孢芽团':'Spore Bud',
 '菌丝束':'Filament Bundle','游走注射器':'Roaming Syringe','缝合钳':'Suture Forceps',
 '悬浮听诊盘':'Floating Stethoscope','自行输液架':'Self-Moving Drip Stand',
 '孢子冠':'Spore Crown','刀片转盘':'Blade Disc','过曝扫描环':'Overexposed Scan Halo',
 '无菌的恩典':'Sterile Grace',
 '白瓷隔断':'White Porcelain Partition','净相壁':'Cleansing Wall','日光壁':'Daylight Wall',
 '净玻璃隔屏':'Clear Glass Screen','罐体密封壁':'Sealed Tank Wall',
 '白瓷工作台':'White Porcelain Workbench','封口药箱':'Sealed Medicine Box',
 '净衣推车':'Clean-Linen Cart','排气口':'Exhaust Vent',
 '淋巴液':'Lymph Fluid','脑脊液':'Cerebral Fluid','洗兆液':'Portent-Wash Fluid',
 '梦醚':'Dream Ether','凝胶基液':'Gel Base','纤维蛋白胶':'Fibrin Gel',
 '晨醒溶液':'Morning-Wake Solution','银盐悬液':'Silver-Salt Suspension','注射用梦水':'Injectable Dream Water',
 '消兆薄雾':'Portent-Clearing Mist','梦醚气':'Dream-Ether Gas','醒素薄气':'Wakeful Haze',
 '无垢蒸汽':'Immaculate Steam','胞尘':'Spore Dust','无菌载气':'Sterile Carrier Gas',
 '端口储有{kind}；每次最多转移 6 单位并消耗一个回合，取消不扣量。':'The port holds {kind}. Transfer at most 6 units for one round; canceling costs nothing.',
 '所有变化都需净化；薄膜与配液开始运行。':'Every change must be cleansed; the membrane and infusion begin operating.',
 '储罐转移了 {kind} ×{n}；剩余 {left}。':'Transferred {kind} ×{n} from the tank; {left} remains.',
 '阀门已经处于所选状态。':'The valve is already in the selected state.',
 '这组灯已经处于所选状态。':'These lamps are already in the selected state.',
 '储罐已经耗尽；它不会自动回充。':'The tank is empty and does not refill automatically.',
 '端口或容器没有剩余容量。':'The port or container has no remaining capacity.',
 '没有可用的兼容容器；请先腾出空间或倒空异种气体。':'No compatible container is available. Make room or empty the other gas first.',
 '端口被阻挡或有异种气体，未排放。':'The port is blocked or contains another gas; nothing was released.',
 '洁净削短了「{name}」的持续。':'Cleansing shortened the duration of {name}.',
 '合法滤过句削短一项可洗材料附着2回合，间隔7回合并遵守同族净化限制；修饰义病原体只限定带有病原体标签的真实目标。':'A legal filtering sentence shortens one washable material attachment by 2 rounds every 7 rounds, respecting shared cleansing limits. Its pathogen modifier requires an actual pathogen-tagged target.',
})

_DESCRIPTION_EN = {
 '排气口':'Natural gas decay doubles in the surrounding 3x3 cells. Vents do not multiply together; sealed floors still preserve gas.',
 '白瓷隔断':'An opaque white porcelain partition. Ordinary sections can be broken to open quiet workrooms.',
 '净相壁':'Every four rounds, adjacent actors shorten one portent by two rounds, positive or negative. Shares its interval with wash fluid.',
 '日光壁':'A porcelain wall containing daylight illuminates three surrounding cells. Both sides can use the light to extend sight.',
 '净玻璃隔屏':'A solid transparent screen. Sight passes through it; creatures and gas cannot.',
 '罐体密封壁':'Solid walls enclose a gas chamber and prevent gas flow while intact.',
 '白瓷工作台':'An aligned white porcelain work surface accessible from adjacent cells.',
 '封口药箱':'A sealed box containing finite supplies.',
 '净衣推车':'A movable clean cart that provides a small piece of cover.',
 '胡桃木书架':'Walnut shelves block sight and straight attacks and can burn down.',
 '推书车':'A wooden cart full of pages can be pushed to change short attack lines and can burn.',
 '防火书柱':'A heavy stone pillar blocks sight and attacks and cannot burn.',
 '黄铜阅读灯':'Illuminates three surrounding cells for both sides. The lamp can be destroyed.',
 '嵌壁梦灯':'A warm breath of light shows through the shade, tinting the two surrounding cells pale beige. It can be switched from an adjacent cell, and its body is fragile: smash it and the niche goes dark for good.',
 '弧光灯架':'Cold white light leaks through the metal mesh with a tang of ozone. It follows the circuit alone: it lights only while that line is energized, dies the moment power is cut, and smashing it gives you no power.',
 '余烬灯盏':'Unburnt embers sit in the lamp; once lit it lights the two cells around it. It burns through itself as any fuel would — the light dies when the flame does, water included.',
 '密封板':'A tightly sealed floor. Legal gas does not decay naturally but can diffuse, react or be extracted.',
 '洁白釉板':'A clean white floor that neither grows plants naturally nor restores extra resources.',
 '干纸堆':'Dry pages form a combustible floor that burns back into ordinary aggregate.',
 '防火石面':'A stone floor that cannot burn and does not change movement speed.',
 '淋巴液':'At four units or more, pathogens alone take two integrity trauma every two rounds.',
 '脑脊液':'At four units or more, multiplies natural Imagination recovery and enemy skill cooldown progress by 1.25, without shortening warnings or recovery windows.',
 '洗兆液':'At four units or more, shortens one portent by three rounds and consumes one unit. The cleansing family has a four-round interval. Evaporates one unit every four rounds.',
 '梦醚':'A combustible pale-purple fluid that converts one unit into dream-ether gas every three rounds.',
 '凝胶基液':'A thick pale-beige base receives a flow budget only once every four rounds.',
 '纤维蛋白胶':'A slowly spreading golden gel flows once every six rounds. At eight units, it halves this cell’s gas-transfer budget.',
 '晨醒溶液':'A bright pale-blue solution converts one unit into wakeful haze every four rounds.',
 '银盐悬液':'Silver-blue particles remain suspended without natural evaporation.',
 '注射用梦水':'A clean carrier for mixing that can extinguish fire. Converts one unit into immaculate steam every six rounds.',
 '消兆薄雾':'A fine cyan mist does not block sight and loses one unit every three rounds on ordinary floors.',
 '梦醚气':'A combustible pale-purple cloud slightly attenuates sight and loses one unit every three rounds on ordinary floors.',
 '醒素薄气':'A bright pale-blue haze does not block sight and loses one unit every three rounds on ordinary floors.',
 '无垢蒸汽':'A thin silver-white steam does not block sight and loses one unit every three rounds on ordinary floors.',
 '胞尘':'A slow cloud of pale-green particles loses one unit every four rounds on ordinary floors.',
 '无菌载气':'A pale-blue inert carrier grants no immunity and loses one unit every four rounds on ordinary floors.',
}
EN_REALMS.update({'周围三乘三格的气体自然消散量加倍；多个排气口不叠乘，密封板仍保气。': 'Natural gas decay doubles in the surrounding 3x3 cells. Vents do not multiply together; sealed floors still preserve gas.', '不透明的白瓷隔断。普通段可破坏，分隔安静的工作间。': 'An opaque white porcelain partition. Ordinary sections can be broken to open quiet workrooms.', '相邻角色每四回合削短一项征兆两回合，不分正负；与洗兆液共享间隔。': 'Every four rounds, adjacent actors shorten one portent by two rounds, positive or negative. Shares its interval with wash fluid.', '内藏日光的白瓷墙，照亮周围三格；敌我都可借光延长视线。': 'A porcelain wall containing daylight illuminates three surrounding cells. Both sides can use the light to extend sight.', '透明的实体隔屏。视线可以穿过，生物与气体不能穿过。': 'A solid transparent screen. Sight passes through it; creatures and gas cannot.', '围合储气室的坚实墙体。完整时阻隔气体流动。': 'Solid walls enclose a gas chamber and prevent gas flow while intact.', '整齐排列的白瓷台面，可以从邻格接近。': 'An aligned white porcelain work surface accessible from adjacent cells.', '封装着有限耗材的箱体。': 'A sealed box containing finite supplies.', '可推动的洁净推车，用作小型移动掩体。': 'A movable clean cart that provides a small piece of cover.', '胡桃木书架阻挡视线与直线攻击，可以被火焰焚毁。': 'Walnut shelves block sight and straight attacks and can burn down.', '装满书页的木车可推动，能改变短线，也会燃烧。': 'A wooden cart full of pages can be pushed to change short attack lines and can burn.', '厚重石柱阻挡视线与攻击，不会燃烧。': 'A heavy stone pillar blocks sight and attacks and cannot burn.', '照亮周围三格，敌我共用灯光；灯体可被破坏。': 'Illuminates three surrounding cells for both sides. The lamp can be destroyed.', '封住细缝的洁白板面。上方气体不自然消散，仍会扩散、反应或被抽取。': 'A tightly sealed floor. Legal gas does not decay naturally but can diffuse, react or be extracted.', '光洁的白色地板，不自然生长植物，也不额外恢复资源。': 'A clean white floor that neither grows plants naturally nor restores extra resources.', '干燥书页铺成地面，可以燃烧并变回普通聚合物。': 'Dry pages form a combustible floor that burns back into ordinary aggregate.', '石质地面不会燃烧，不改变行走速度。': 'A stone floor that cannot burn and does not change movement speed.', '四单位以上时，仅对病原体每两回合造成两点完整度创伤。': 'At four units or more, pathogens alone take two integrity trauma every two rounds.', '四单位以上时，想象自然恢复和异象技能冷却推进乘以1.25；不缩短预警和恢复。': 'At four units or more, multiplies natural Imagination recovery and enemy skill cooldown progress by 1.25, without shortening warnings or recovery windows.', '四单位以上削短一项征兆三回合，消耗一单位；净化族间隔四回合。每四回合蒸发一单位。': 'At four units or more, shortens one portent by three rounds and consumes one unit. The cleansing family has a four-round interval. Evaporates one unit every four rounds.', '淡紫色可燃液体，每三回合将一单位转为梦醚气。': 'A combustible pale-purple fluid that converts one unit into dream-ether gas every three rounds.', '浓稠的淡米色基液，每四回合才流动一格。': 'A thick pale-beige base flows only one cell every four rounds.', '缓慢铺开的金色胶液，每六回合流动一次；攒到八单位时，胶液糊住缝隙，气也过得慢了。': 'A slowly spreading golden gel flows once every six rounds. At eight units the gel clogs the gaps and gas passes more slowly.', '明亮浅蓝的溶液，每四回合将一单位转为醒素薄气。': 'A bright pale-blue solution converts one unit into wakeful haze every four rounds.', '银蓝色颗粒悬浮其中，不会自然挥发。': 'Silver-blue particles remain suspended without natural evaporation.', '洁净的配液载体，可以灭火；每六回合将一单位转为无垢蒸汽。': 'A clean carrier for mixing that can extinguish fire. Converts one unit into immaculate steam every six rounds.', '浅青细雾，不阻挡视线；普通地面每三回合减少一单位。': 'A fine cyan mist does not block sight and loses one unit every three rounds on ordinary floors.', '可燃的淡紫气团，略微衰减视线；普通地面每三回合减少一单位。': 'A combustible pale-purple cloud slightly attenuates sight and loses one unit every three rounds on ordinary floors.', '明亮浅蓝的薄气，不阻挡视线；普通地面每三回合减少一单位。': 'A bright pale-blue haze does not block sight and loses one unit every three rounds on ordinary floors.', '银白色的稀薄蒸汽，不阻挡视线；普通地面每三回合减少一单位。': 'A thin silver-white steam does not block sight and loses one unit every three rounds on ordinary floors.', '浅绿小粒构成的缓慢气团；普通地面每四回合减少一单位。': 'A slow cloud of pale-green particles loses one unit every four rounds on ordinary floors.', '淡蓝的惰性载体，不赋予免疫；普通地面每四回合减少一单位。': 'A pale-blue inert carrier grants no immunity and loses one unit every four rounds on ordinary floors.', '换气扇·北': 'Ventilation Fan: North', '向北吹风，每回合将前方六格内的气体向前推一格；墙与满格会阻挡，不同气体不强制混合，总气量保持不变。': 'Blows north: each round, moves gas within six cells ahead one cell forward. Walls and full cells block flow; different gases are not forced to mix, and total gas is preserved.', '换气扇·东': 'Ventilation Fan: East', '向东吹风，每回合将前方六格内的气体向前推一格；墙与满格会阻挡，不同气体不强制混合，总气量保持不变。': 'Blows east: each round, moves gas within six cells ahead one cell forward. Walls and full cells block flow; different gases are not forced to mix, and total gas is preserved.', '换气扇·南': 'Ventilation Fan: South', '向南吹风，每回合将前方六格内的气体向前推一格；墙与满格会阻挡，不同气体不强制混合，总气量保持不变。': 'Blows south: each round, moves gas within six cells ahead one cell forward. Walls and full cells block flow; different gases are not forced to mix, and total gas is preserved.', '换气扇·西': 'Ventilation Fan: West', '向西吹风，每回合将前方六格内的气体向前推一格；墙与满格会阻挡，不同气体不强制混合，总气量保持不变。': 'Blows west: each round, moves gas within six cells ahead one cell forward. Walls and full cells block flow; different gases are not forced to mix, and total gas is preserved.'})

EN_REALMS.update({
'薄膜裹着一滴安静的液体，边缘却一直颤动。它碰到你便缩回一格；淋巴液能损伤这层病原体膜。':'A trembling membrane holds a quiet drop. It retreats one cell after touching you; lymph fluid damages its pathogen membrane.',
'透明衣壳像细小针尖排列。针线先在地板上留下提示，随后才射出；横移与实体墙都能挡住它。':'Transparent capsids form tiny needle points. A needle line marks the floor before firing; stepping aside or solid walls can stop it.',
'一簇洁白孢芽，像没有开封的培养样本。它只带着有限胞尘；诱入浅槽比站在雾里硬撑更稳妥。':'A white spore bud resembles an unopened culture. Its spore dust is finite; lure it into a shallow tray rather than endure its mist.',
'菌丝束沿地板接缝舒展，像误写在白瓷上的缝线。两格迟线不会把你钉死，离开预告即可避开。':'Mycelium spreads along floor seams like misplaced stitches. Its two-cell slowing line cannot immobilize you; leave the warning cells to evade.',
'细长器械自行滑行，针尖总比身体先转向。推进一旦起手便锁定方向，撞上实体后停止。':'The slender device slides by itself, its needle turning first. A dash locks its direction at windup and stops at solid obstacles.',
'一对没有手握住的钳口，在空中轻轻开合。牵引先显出短线，不会把目标拉进墙里。':'Ungrasped forceps open and close in the air. A short line warns before pulling; targets are never pulled into walls.',
'金属听诊盘浮在一条看不见的软管末端。它只广播一次已听见或看见的位置，消息不会追着你的新位置更新。':'A listening disc floats on an unseen tube. It broadcasts one previously heard or seen position once; the report never follows your new position.',
'银架推着最后几滴浅蓝配液。储量耗尽便不能继续滴注；地上的脑脊液也可能成为你的恢复点。':'A silver stand carries its last pale-blue drops. Infusion stops when its reserve runs out; spilled cerebral fluid may also help you recover.',
'培养皿般的圆冠悬在病原体上方。短时菌膜可以洗掉；胞尘储量有限，它不会无休止地产雾。':'A dish-like crown floats above the pathogen. Its temporary membrane is washable; finite spore dust prevents endless mist.',
'三枚刀片在洁净圆盘上轮换着反光。弧扫只落在起手时标出的三格，扫完需要停顿。':'Three blades flash on a clean disc. The arc hits only the three cells marked at windup and must pause afterward.',
'一圈过亮的扫描镜缓慢旋转。它的灯也照亮你的目标；扫描线不会跟随你移动。':'An overbright scan ring turns slowly. Its light also reveals your targets; the scan line never tracks your movement.',
'银白环状灭菌设备包着透明核心。它相信清除所有变化就能永远安全；有限配液、可关闭阀门与会洗掉敌我征兆的稀疏环，是它留下的矛盾。':'A silver-white sterilizer surrounds a transparent core. It believes removing all change creates lasting safety, yet leaves finite fluid, closable valves and sparse rings that wash omens from both sides.',
})

REALM_EFFECT_LABELS={
'hospital_cerebral_ampoule':'脑脊流畅','hospital_fever':'热兆削短','hospital_fluent':'想象恢复流畅','hospital_gel_buffer':'一次创伤缓冲','hospital_glass_rib':'玻璃支撑','hospital_hollow_lancet':'真实材料注入','hospital_immune_once':'一次负兆缓冲','hospital_lumen_mask':'照明识别','hospital_lymph_filter':'材料滤过','hospital_lymph_hit':'一次病原体强化','hospital_marrow_spoon':'摄入恢复补充','hospital_oxygen':'胞尘防护','hospital_pain_buffer':'一次心智缓冲','hospital_positive_choice':'正兆转清醒','hospital_pulse_tag':'短声呼应','hospital_safe_sleep':'安全静养恢复','hospital_saline':'心智清醒恢复','hospital_sensitive':'跨资源恢复补充','hospital_sterile_glove':'征兆清洗','hospital_suture_coil':'一次缝合缓冲','hospital_suture_shears':'材料附着剪除','hospital_tool':'医疗材料工具','hospital_wake':'沉眠削短','hospital_wash_choice':'自选征兆削短','library_bookmark':'跨门修正','library_card':'状态变化观察','library_fold':'邻室连接辨认','library_index':'已知弱点提示','library_lens':'观察汇聚','library_paperweight':'独处恢复','library_quill':'一次弱控制抵消','library_testimony':'锁定替代提示'}
_EFFECT_EN=('Cerebral Fluency','Shorten Heat Omens','Fluent Imagination Recovery','One Trauma Buffer','Glass Support','Inject Actual Materials','One Negative-Omen Buffer','Identify in Light','Filter Materials','One Pathogen Hit Boost','Ingestion Recovery Supplement','Spore-Dust Protection','One Mind-Trauma Buffer','Convert Positive Omen to Lucidity','Brief Sound Response','Safe Rest Recovery','Restore Mind and Lucidity','Cross-Resource Recovery Supplement','Wash Omens','One Suture Buffer','Sever Material Attachment','Clinical Material Tool','Shorten Sleep Omens','Shorten a Chosen Omen','Doorway Adjustment','Observe State Changes','Identify Adjacent-Room Connections','Known Weakness Hint','Combine Observations','Solitary Recovery','Cancel One Weak Control','Alternative Lock-On Hint')
EN_REALMS.update(dict(zip(REALM_EFFECT_LABELS.values(),_EFFECT_EN)))

EN_REALMS.update({
'近战实体创伤6、耗时1.3；合法命中剪除目标一项可洗征兆2回合，先处理附着；共享间隔7回合。':'Melee Integrity trauma 6, time 1.3. A legal hit shortens one washable target omen by 2 rounds, attachment first; shared interval 7 rounds.',
'4格短射线实体创伤5；选择液体容器装载最多6单位一种真实样本。合法命中注入1单位，实际扣量；注入间隔6回合，空针仍可普通攻击。':'A short 4-cell ray deals 5 Integrity trauma. Load up to 6 units of one actual liquid sample. A legal hit injects and consumes 1 unit every 6 rounds; an empty lancet can still attack normally.',
'受击后的合法缝合句给予下一次创伤减1，最长6回合；与凝片、凝胶共享一份缓冲和8回合间隔。修饰义相接限制邻接目标。':'A legal suture sentence after being hit reduces the next trauma by 1 within 6 rounds. Shares one buffer and an 8-round interval with gel effects. Connected modifies the sentence to adjacent targets.',
'合法滤过句削短一项可洗材料附着2回合，间隔7回合并遵守同族净化限制；修饰义病原体只限定真实pathogen目标。':'A legal filter sentence shortens one washable material attachment by 2 rounds every 7 rounds, respecting shared cleansing limits. The pathogen modifier applies only to actual pathogen targets.',
'施法后的合法流畅句使想象自然恢复倍率取最大1.25，持续6回合；基础恢复为0仍为0，不增加想象上限。':'A legal fluent sentence after casting raises natural Imagination recovery to at most ×1.25 for 6 rounds. A zero base remains zero; the maximum does not increase.',
'合法受击防御反应削短自身一项可洗征兆2回合，正负皆可；间隔7回合并共享同族净化限制，不清除技能冷却。':'A legal defensive reaction to being hit shortens one of your washable omens, positive or negative, by 2 rounds. Shared cleansing interval 7 rounds; skill cooldowns remain.',
'在光中受击后的支撑句给予下一次创伤减1，最长6回合；与凝胶共享一份缓冲及8回合间隔，不提供永久屏障。':'A support sentence after being hit in light reduces the next trauma by 1 within 6 rounds. Shares one buffer and an 8-round interval with gel; grants no permanent barrier.',
'合法受击后呼应句发出半径3的短声源；7回合间隔，同一根行动只呼应一次。':'A legal response sentence after being hit emits a brief sound within radius 3, every 7 rounds; only once per root action.',
'合法摄入后句让一次真正恢复的单种资源额外恢复至多2点；8回合间隔，派生恢复不会触发自己或其他恢复反馈。':'A legal after-ingestion sentence adds up to 2 to one actually restored resource, every 8 rounds. Derived recovery triggers neither this effect nor other recovery feedback.',
'合法照见句在已照亮的位置识别半径2内真实视线可达的伪装3回合，7回合间隔；不会透墙、全图揭示或提供永久护甲。':'A legal reveal sentence identifies disguises for 3 rounds within radius 2 of a lit position and actual line of sight, every 7 rounds. Never sees through walls, reveals the entire map or grants permanent armor.',
})

EN_REALMS.update({
'{name}：操作已完成，库存与奖励已记录。':'{name}: completed; stock and rewards have been recorded.',
'当地服务完成；库存已记账。':'Local service completed; stock has been recorded.','推车移了一格。':'The cart moved one cell.',
'设备已停服；当地记录与撤离仍可使用。':'The device has stopped serving; local records and evacuation remain available.',
'核心停机了。记录台的三选一主要报酬已开放。':'The core has shut down. Choose one of three main rewards at the record desk.',
'设备停止可选服务。':'The device has stopped its optional services.','设备发出警告；再次破坏将停止服务。':'The device warns you: further damage will stop its services.',
'推车不能推入主路、出口或目标锚点。':'The cart cannot be pushed onto the main route, exits or scene anchors.',
'需要容器中的{material}×2；尚未支付。':'Requires {material} ×2 in a container; nothing has been paid.',
'服务记录不存在。':'No service record exists.','基础容器已领取。':'The basic containers have already been received.','准备物资已领取。':'The preparation supplies have already been received.',
'本地灯段已检修，耗材已用完。':'The local light segment has been repaired; its supplies are spent.','标示灯段仍然亮着，无需检修。':'The marked light segment is still lit; no repair is needed.',
'请先恢复回风服务格。':'Restore the return-air service cell first.','当地仍有可见危险。':'A local hazard is still visible.','材料观察记录：{records}':'Material observations: {records}',
'未知服务。':'Unknown service.','气罐实际剩余：{volumes}':'Actual tank reserves: {volumes}','转移{material}×{amount}；剩余{volume}。':'Transferred {material} ×{amount}; {volume} remains.',
'此设施不在当前疗所。':'This facility is not in the current sanctuary.','请先接近设施。':'Approach the facility first.',
'药柜已停止服务；药箱与主路仍可使用。':'The dispenser has stopped serving; medicine boxes and the main route remain accessible.',
'此处库存或奖励已经领取。':'The stock or reward here has already been claimed.','先观察入口浅槽；可以沿干路绕行，不要求击败病原体。':'Observe the entrance tray first. You may use the dry route; defeating the pathogen is optional.',
'三资源不足，尚未支付。':'Insufficient resources; nothing has been paid.','目前没有可洗征兆。':'There is no washable omen at present.','物品尚未登记，未支付。':'The item is not registered; nothing has been paid.',
'核心仍在运行；奖励尚未开放。':'The core is still operating; rewards are not yet available.','主要报酬已记账；记录仍可阅读。':'The main reward has been recorded; you may still read the records.',
'装备尚未登记，未领取。':'The equipment is not registered; nothing has been claimed.','尚未连续保持三回合安全。':'You have not remained safe for three consecutive rounds.',
'胞尘仍堵住服务格；先排气、吸附、洗液处理或沿干路绕行。':'Spore dust still blocks the service cell. Vent, absorb or wash it away, or take the dry route.',
'此处没有灯段。':'There is no light segment here.','储液已耗尽。':'The fluid reserve is empty.','没有兼容容器容量；未消耗储液。':'No compatible container has capacity; no fluid was consumed.','未知当地操作。':'Unknown local operation.',
'脑脊液：流畅':'Cerebral fluid: fluency','净化：计时缩短':'Cleansing: shorter duration','淋巴液：病原体损伤':'Lymph fluid: pathogen damage',
'有限器械柜':'Finite Instrument Cabinet','四选一器械储量，仅领取一件。满行囊时物品留在柜旁，领取记录不会重置。':'Choose one of four instruments once. If your bag is full, the item remains beside the cabinet; its claim record never resets.',
'改选另一份恢复药与两份战术药（仍仅领取三份）':'Choose the other recovery medicine with two tactical medicines; still only three doses.',
'三份封存药物；开箱一次，未领取物品留在此地，不刷新。':'Three sealed doses, opened once. Uncollected items remain here; stock never refreshes.',
})
for _name in ('不闭合的手术剪','空心针','缝合线圈','淋巴滤环','脑脊安瓿','无垢手套','玻璃肋','心搏标签','骨髓银匙','白昼面罩'):
    EN_REALMS['领取'+_name]='Receive '+EN_REALMS[_name]

EN_REALMS.update({
'分诊铃':'Triage Bell','无手药柜':'Handless Dispenser','净衣护理车':'Clean-Linen Care Cart','滴瓶看守':'Infusion Keeper','第一份干净样本':'The First Clean Sample','没写完的标签':'The Unfinished Label','封死的气室':'The Sealed Gas Chamber','安静的回风口':'The Quiet Return-Air Duct','过长的白昼':'The Overlong Day','洗掉什么':'What to Wash Away','尚未使用的静养湾':'The Unused Rest Bay','停机后的恩典':'Grace After Shutdown','有限储液架':'Finite Fluid Stand','配液记录台':'Infusion Record Desk',
'暂不操作':'Do nothing for now','使用静养设备：心智+4':'Use the rest device: Mind +4','使用静养设备：清醒+4':'Use the rest device: Lucidity +4','检查回风服务格':'Inspect the return-air service cell','关闭本地灯段并记录侧室路线':'Switch off the local lights and note the side-room route','阅读实际罐内容与剩余量':'Read the actual tank contents and remaining quantities','阅读已观察的材料效果':'Read observed material effects','向兼容容器抽取至多6单位':'Draw up to 6 units into a compatible container','领取封存药物（满行囊留在箱内）':'Receive the sealed medicines; leave them here if your bag is full','封装蓝绿淋巴样本（2单位）':'Seal the blue-green lymph sample (2 units)','封装透明洗兆样本（2单位）':'Seal the clear omen-wash sample (2 units)','取样并选择载氧棉糖':'Sample and choose Oxygen-Cotton Candy','取样并选择淋巴素软胶囊':'Sample and choose a Lymph Capsule','用真实洗兆液削短一项并选洗忆泡腾片':'Use actual omen-wash fluid, then choose a Memory-Wash Tablet','用真实洗兆液削短一项并选晨醒含片':'Use actual omen-wash fluid, then choose a Morning-Wake Lozenge',
'容许差异：缝合线圈':'Allow differences: Suture Coil','带走未完成的配液：无垢银剪':'Carry away an unfinished mixture: Unclosed Surgical Shears','保持纯净：白昼面罩':'Preserve purity: Daylight Mask',
'浅槽中的淋巴液会损伤病原体；诱入、击败或沿干路绕过后，携带真实样本即可封装。':'Lymph fluid in the shallow tray damages pathogens. Lure one in, defeat it or use the dry route, then seal an actual carried sample.',
'蓝绿标签写着“膜边收缩”，透明标签写着“计时缩短”。封装会实际消耗所选样本；标签不符可以重选。':'The blue-green label says “membrane edges contract”; the clear one says “durations shorten”. Sealing consumes the chosen actual sample. A mismatched label can be corrected.',
'端口可抽取、定量排放或保留；阅读不改变材料布局。实际使用权在各罐端口。':'Tank ports allow drawing, measured venting or preservation. Reading changes no material layout; operate each actual port to use it.',
'服务格有有限胞尘；排气、滤膜吸附、洗液反应均可恢复它。干路不受任务锁。':'The service cell contains finite spore dust. Venting, filter absorption or washing can restore it. The dry route remains open regardless of this task.',
'附近灯段同时扩大双方视野。关闭后可借不透明侧室遮挡；仅记录这一处路线。':'Nearby lights extend sight for both sides. Switch them off and use opaque side rooms as cover; only this local route is recorded.',
'需要容器中洗兆液2单位以及当前一项可洗征兆；正负都可洗。停止净化不消耗。':'Requires 2 units of omen-wash fluid in a container and one current washable omen, positive or negative. Stopping consumes nothing.',
'站在此处邻接范围，连续保持三回合安全即可使用。设备仅有一次储量，不增加上限。':'Remain adjacent and safe for three consecutive rounds to use the device. Its reserve lasts once and never increases resource maxima.',
'核心停机后可领取一件主要装备。线圈：状态编织；银剪：材料操作；面罩：照明防护。记录与首领奖励共用一笔账。':'After core shutdown, choose one main instrument: the coil for status weaving, shears for materials or mask for lighting protection. The record and boss reward share one claim.',
'看守离场或损坏后仍可阅读；不会重复授予奖励。':'Records remain readable after the keeper leaves or is damaged; no reward is granted twice.',
'储液12单位，不会回充；容器容量不足时只转移实际可装数量。':'Reserve: 12 fluid units, never refilled. Transfers are limited to actual available container capacity.',
'独立库存，只能配制一份；真实材料与三资源支付。满行囊则存入本地奖励箱。':'Independent stock allows one preparation, paid with actual materials and all three resources. A full bag leaves the reward here.',
'淋巴液只损伤病原体；灯光也照见你。干路和撤离始终开放。':'Lymph fluid damages only pathogens; light also reveals you. Dry routes and evacuation are always available.',
'库存一份；配制实际消耗材料与三资源。':'One preparation in stock; it consumes actual materials and all three resources.',
'排掉标出的胞尘后，我可以守护一次本地服务点。':'Clear the marked spore dust, and I can guard this local service point once.',
'核心的供液有限；阀门和灯段可手动控制。设备停止后记录仍在。':'The core has finite fluid. Valves and light segments are manually controlled; records survive shutdown.',
'领取一次基础液/气容器':'Receive the basic liquid and gas containers once','恢复附近已关闭的灯段（耗材一次）':'Restore nearby switched-off lights; supplies last once','使用一次守护服务（安全时心智+4）':'Use one guarding service: Mind +4 while safe','阅读材料效果记录':'Read material-effect records','一次准备：缓释凝片':'One preparation: Slow-Release Gel Tablet','一次准备：载氧棉糖':'One preparation: Oxygen-Cotton Candy',
'配制洗忆泡腾片：洗兆液2，心智1/清醒1/想象2':'Prepare Memory-Wash Tablet: wash fluid 2, Mind 1/Lucidity 1/Imagination 2','配制淋巴胶囊：淋巴液2，心智1/清醒1/想象2':'Prepare Lymph Capsule: lymph fluid 2, Mind 1/Lucidity 1/Imagination 2',
'配制洗忆泡腾片（洗兆液2，心智1/清醒1/想象2）':'Prepare Memory-Wash Tablet (wash fluid 2, Mind 1/Lucidity 1/Imagination 2)','配制淋巴胶囊（淋巴液2，心智1/清醒1/想象2）':'Prepare Lymph Capsule (lymph fluid 2, Mind 1/Lucidity 1/Imagination 2)',
'可见目标与合法空格。':'A visible target and a legal unoccupied cell.','横移、遮挡、走侧廊。':'Step aside, take cover or use a side passage.','目标在视线内；储量不足时停用。':'Target must be in line of sight; disabled when its reserve is insufficient.','横移、遮挡、利用有限材料与双向净化。':'Step aside, take cover, or use finite materials and cleansing that affects both sides.',
'锁定至多五格针线；单次清醒创伤6，实体墙可截断。':'Locks a needle line of up to 5 cells; deals 6 Lucidity trauma once. Solid walls interrupt it.',
'普通每次4单位胞尘分至多两格，孢子冠每次6单位分至多四格；总预算12。':'Ordinary casts divide 4 spore-dust units across at most 2 cells; the crown divides 6 across at most 4. Total reserve: 12.',
'目标附近两格短线，命中附加两回合迟拍；无直接创伤，不硬定身。':'A short two-cell line near the target applies slowing for 2 rounds on hit; no direct trauma or immobilization.',
'锁定直线推进至多两格，撞实体停止；警示线上单次清醒创伤7。':'Dashes up to 2 cells along a locked line, stopping at solid obstacles; deals 7 Lucidity trauma once along the warning line.',
'预告后把仍在锁定线上的目标牵引一格；不拉入实体或占用格。':'After warning, pulls a target still on the locked line by one cell; never into solid or occupied cells.',
'仅一次广播起手时的真实最后目击位置；不传递玩家的新坐标。':'Broadcasts the actual last-seen position at windup once; never reports the player’s new coordinates.',
'每次在局部至多三格滴下总计2单位脑脊液，遭遇预算6。':'Drips a total of 2 cerebral-fluid units onto at most 3 nearby cells per cast; encounter reserve: 6.',
'给予自身三回合菌膜；挡一次命中的1点创伤，可洗除，无回血。':'Grants a washable membrane for 3 rounds, reducing one hit by 1 trauma; restores no Integrity.',
'锁定目标附近三格弧线；单次清醒创伤10，至少恢复一回合。':'Locks a three-cell arc near the target; deals 10 Lucidity trauma once and recovers for at least one round.',
'锁定至多六格射线，清醒创伤9；自身位置临时照亮半径2，三回合后恢复。':'Locks a ray of up to 6 cells for 9 Lucidity trauma; temporarily lights radius 2 around itself, reverting after 3 rounds.',
'锁定至多七格细线，单次清醒创伤9；横移或新增实体墙可规避。':'Locks a thin line of up to 7 cells for 9 Lucidity trauma once; stepping aside or adding a solid wall evades it.',
'预告两回合，周围八格稀疏环；敌我一项可洗征兆缩短3，心智创伤5。':'Warns for 2 rounds, then affects a sparse ring of 8 nearby cells: shortens one washable omen by 3 on either side and deals 5 Mind trauma.',
'在首次确定的至多三个槽格每次配液6，总储量12；脑脊液同时帮助敌我。':'Delivers 6 fluid units per cast into at most 3 slots fixed on first use; total reserve 12. Cerebral fluid helps both sides.',
'第二阶段后预告两回合，召唤完整度6、创伤3的膜泡；最多两次，同时至多一只，无奖励。':'After phase two, warns for 2 rounds and summons a membrane with Integrity 6 and trauma 3. At most two summons, one alive at a time; no rewards.',
})
for _material in ('无菌载气','胞尘','醒素薄气'):
    _english={'无菌载气':'sterile carrier gas','胞尘':'spore dust','醒素薄气':'wakeful vapor'}[_material]
    EN_REALMS[f'罐内存有{_material}。每次至多转移 6 单位；操作消耗一回合，取消免费。']=f'The tank contains {_english}. Transfer up to 6 units per operation; costs one round, cancelling is free.'

EN_REALMS.update({
'索引员':'Indexer','借阅员':'Librarian','校勘员':'Collator','守页人':'Page Keeper','窗边读者':'Reader by the Window',
'错页索引柜':'Misfiled-Page Index Cabinet','双声校勘台':'Two-Voice Collation Desk','同庭异窗':'Different Windows, One Courtyard','目录查询台':'Catalogue Inquiry Desk','中央誊本台':'Central Fair-Copy Desk','一次借阅的藏品柜':'Single-Loan Collection Cabinet','阅读灯控制台':'Reading-Lamp Console',
'询问通路与规则':'Ask about routes and rules','告辞':'Farewell','保持现状':'Keep the current state','暂不回应':'Do not respond yet','复位':'Reset','整理目录':'Organize the catalogue','比较两个窗口':'Compare the two windows','记下记录':'Note the record','拒绝被定稿，回应未尽目录':'Refuse a final definition; answer the Unfinished Catalogue','归还借阅记录，返回主梦':'Return the loan record and go back to the main dream','关闭阅读灯':'Switch off reading lamps','点亮阅读灯':'Switch on reading lamps','稍后借阅':'Borrow later',
'只控制本层固定阅读灯，双方视野同样改变。':'Controls only the fixed reading lamps on this floor; sight changes equally for both sides.',
'开关消耗一行动；地上已有的材料保持原状。':'Switching costs one action; materials already on the floor remain unchanged.',
'只能借出一件，取消与满行囊不会消耗借阅资格。':'Only one item may be borrowed; cancelling or a full bag does not consume your loan eligibility.',
'选择一种观看世界的方式；另选一件不会刷新借阅资格。':'Choose one way of seeing the world; choosing another item does not renew loan eligibility.',
'可选阅读与整理，不影响主路。':'Reading and organizing are optional; the main route stays open.',
'返回主梦的页码不会消失。':'The page number leading back to the main dream never disappears.',
'这里的材料、书架与已领取奖励将保持原状。':'Materials, shelves and already claimed rewards here will remain as they are.',
'页码可以重排，记忆不必重演。湿墨只在侧路；横向索引廊能避开长线。':'Page numbers can be rearranged without replaying memories. Wet ink stays on side routes; crosswise index corridors evade long lines.',
'每个声音都需要一间自己的房间。纸堆有限，书车可逆整理；校勘不是必经谜题。':'Every voice needs a room of its own. Paper piles are finite and book carts can be rearranged reversibly; collation is an optional puzzle.',
'同一庭院有多个窗口。灯光照亮双方，干燥回廊可以避开水与导电区。':'One courtyard has many windows. Lamps light both sides; dry galleries avoid water and conductive areas.',
'目录提供位置，不提供许可。书架挡住追问；推书车能改变短线，但中轴始终畅通。':'The catalogue gives locations, not permission. Shelves block inquiries and movable book carts change short lines; the central axis stays open.',
'目录试图替你定稿。三份记录可以免费阅读；只有确认回应誊本台才开始战斗。':'The catalogue tries to define you conclusively. Three records may be read freely; combat begins only after you confirm your response at the fair-copy desk.',
'未尽目录问：你愿意接受唯一、永久正确的定义吗？':'The Unfinished Catalogue asks: will you accept one definition that is permanently correct?',
'阅读与取消不会开战。确认后可通过多条回廊避开索引线。':'Reading or cancelling never starts combat. After confirmation, several galleries allow you to evade index lines.',
'观察免费；复位不会重复领取奖励。':'Observation is free; resetting never grants the reward twice.',
'秩序保护人：被保存的人不必再怕遗忘。':'Order protects people: those preserved need no longer fear being forgotten.',
'秩序删掉人：所有不合目录的声音都被擦去。':'Order erases people: every voice that does not fit the catalogue is removed.',
'人主动请求被保留：并非每一次归档都是强迫。':'A person asks to be preserved: archiving is not always forced.',
'完整索引不等于完整的人。':'A complete index is not a complete person.',
'划线':'Underline','删改':'Revise','回目':'Return to Entry','异文誊影':'Copy Variant Shadow','引灯':'Guide the Lamp','归目':'File in Catalogue','折步':'Folded Step','收页':'Gather Pages','最后一页':'The Last Page','校订':'Collate','留白':'Leave Blank','省略':'Omit','短距追问':'Short Inquiry','错页':'Misfiled Page','阈限':'Threshold',
})
for _name in ('划线','删改','回目','异文誊影','引灯','归目','折步','收页','最后一页','校订','留白','省略','短距追问','错页','阈限'):
    EN_REALMS[_name+'：锁定预告格，有限资源与实体遮挡。']=EN_REALMS[_name]+': locks the warned cells, with finite reserves and solid cover.'
for _name in ('门前书签','失时索引','隐城折页','留白纸镇','阿莱夫透镜','拒誊羽笔','蝶梦借阅证','罗生门残页'):
    EN_REALMS['借阅'+_name]='Borrow '+EN_REALMS[_name]
for _index in range(1,4): EN_REALMS[f'矛盾记录·{_index}']=f'Contradictory Record {_index}'


def translate_composed(text):
    """Translate authored preview lines without translating their shape symbols."""
    if not isinstance(text,str):
        return None
    for name in ('不闭合的手术剪','缝合线圈','白昼面罩'):
        if text.startswith(name+' '):
            rest=text[len(name)+1:]
            pattern,separator,description=rest.partition(' ')
            if description in EN_REALMS:
                return EN_REALMS[name]+' '+pattern+' '+EN_REALMS[description]
    return None

EN_REALMS.update({
'未尽目录翻到删改页；旧的索引预告被收回。':'The Unfinished Catalogue turns to its revision page; previous index warnings are withdrawn.',
'未尽目录不再替你定稿。中央誊本台等待你的选择。':'The Unfinished Catalogue no longer defines you conclusively. The central fair-copy desk awaits your choice.',
'你借出了{name}。这座藏品柜保留一次借阅的记录。':'You borrowed {name}. This collection cabinet records its one loan.',
'拒誊羽笔拒绝了一次弱控制；这两行动内耐受同类控制。':'The Quill of Refusal cancels one weak control effect; you resist that control family for the next two actions.',
'蝶梦借阅证记下这次环境变化：四回合内视野增加两格。':'The Butterfly-Dream Library Card records this change of surroundings: sight range +2 for four rounds.',
'隐城折页翻过一遍：这一层通向未知的边界都已经记下了。':'The Invisible-City Fold turns its page: every boundary into the unknown on this layer is already recorded.',
'{dir} {distance} 格（{cell}）':'{dir}, {distance} cells ({cell})',
'隐城折页折出最近的未知边界：{edges}；只标边界，不记那边有什么。':'The Invisible-City Fold creases out the nearest boundaries into the unknown: {edges}. It marks the boundary only; nothing beyond it is recorded.',
'失时索引认出了{name}：完整度 {integrity}，可借书架遮断它的射线。':'The Index of Lost Time recognizes {name}: Integrity {integrity}. Shelves can block its rays.',
'阿莱夫透镜汇聚了一格范围内的观察：{names}。':'The Aleph Lens combines observations within one cell: {names}.',
'罗生门残页保留另一份见证：邻格 {cell} 可作为下一次锁定的替代站位。':'The Rashomon Fragment preserves another testimony: adjacent cell {cell} is an alternative position for the next lock-on.',
})

EN_REALMS.update({
'索引柜目前页码为{pages}；相邻两页可交换，正序会指出收藏位置。':'The index cabinet’s current page order is {pages}. Swap adjacent pages; the correct order reveals the collection location.',
'两组书稿目前为{drafts}；并置会采用同一阅读次序，复位保留领取记录。':'The two drafts currently read {drafts}. Juxtaposing uses the same reading order; resetting preserves the claim record.',
})

EN_REALMS.update({
 '罐内存有{kind}。每次至多转移 6 单位；操作消耗一回合，取消免费。':'The tank holds {kind}. Transfer at most 6 units for one round; canceling is free.',
 '仍有变化，仍需净化。银白环停顿了一拍。':'Change remains, and so does the need for cleansing. The silver ring pauses for a beat.',
 '储罐已经耗尽，不会自动回充。':'The tank is empty and does not refill automatically.',
 '没有可容纳此气体的容器，请腾出容量或倒空异种气体。':'No container can hold this gas. Make room or empty the other gas first.',
 '合法滤过句削短一项可洗材料附着2回合，间隔7回合并遵守同族净化限制；修饰义病原体只限定具有病原体标签的真实目标。':'A legal filtering sentence shortens one washable material attachment by 2 rounds every 7 rounds, respecting shared cleansing limits. Its pathogen modifier requires an actual pathogen-tagged target.',
})
for _library_name in ('未借出的读者','门前迟疑者','倒写的页码','擦去的旁白','迟到的索引','借光的校对者','折页行者','散页装订者','无人称抄写员','多版本见证','拒绝誊清者','未尽目录'):
    EN_REALMS[_library_name+'保存着尚未定稿的可能。技能先标出落点，书架与侧廊提供避让。']=(
        EN_REALMS[_library_name]+' preserves possibilities that remain unfinished. Skills mark their target cells first; shelves and side galleries provide room to evade.')

EN_REALMS.update({
'交换两张页码':'Swap the two page numbers','并置两组书稿':'Juxtapose the two drafts','查询收藏位置':'Query collection locations','离开藏品柜':'Leave the collection cabinet',
'这条借阅记录不属于当前层。':'This loan record does not belong to the current floor.','阅读灯已点亮。':'The reading lamps are on.','阅读灯已关闭。':'The reading lamps are off.',
'目录与两份页码可以互相对照；整理可撤销，奖励仅领取一次。':'Compare the catalogue with both sets of page numbers. Organizing is reversible; its reward may be claimed once.',
'页码回到初始位置；已领取奖励保持记录。':'Page numbers return to their initial positions; claimed rewards remain recorded.','这份目录已经整理。':'This catalogue is already organized.',
'目录指出一条干燥回廊；校勘补充了两点实际缺损的想象力。':'The catalogue identifies a dry gallery; collation restores up to 2 actually missing Imagination.',
'记录已保留；你仍可提出自己的版本。':'The record is preserved; you can still offer your own version.',
'已被收录，但目录仍允许变化。记录已保留；你仍可提出自己的版本。':'You are catalogued, yet the catalogue still permits change. The record is preserved; you may offer your own version.',
'这一次借阅已经登记。':'This loan has already been recorded.','意识行囊已满；借阅资格保留。':'Your bag is full; loan eligibility is preserved.',
'未尽目录已被回应。':'The Unfinished Catalogue has already received a response.','誊本台前被占据；腾出位置后再回应。':'The space before the fair-copy desk is occupied; clear it before responding.',
'未尽目录开始写下你的定义；索引线会先预告落点。':'The Unfinished Catalogue begins writing your definition; index lines warn of their target cells first.',
'目录上的选择已经保存，或战斗尚未结束。':'Your catalogue choice is already saved, or combat has not ended.',
'意识行囊已满；目录会保留选择，整理后再借书。':'Your bag is full; the catalogue preserves your choice. Make room before borrowing.',
'你保存目录，也保留被收录者改变自己的余地。':'You preserve the catalogue and leave those within it room to change.',
'空页不是错误；你把尚未定义的空间留给自己。':'A blank page is not an error; you leave yourself room that remains undefined.',
'你带走尚未写完的索引；它只辨认已遇见的人，不能替世界定稿。':'You carry away an unfinished index. It recognizes only those already encountered; it cannot define the world conclusively.',
'没有可执行的借阅操作。':'No loan operation is available.',
})

# Revised player-facing equipment descriptions. Keep the Chinese source text
# in item definitions and use these translations for the English UI.
from .data.items import ITEM_DEFINITIONS as _ITEM_DEFINITIONS

EN_REALMS.update({
    _ITEM_DEFINITIONS['hospital.suture_shears']['description']:
        'Melee deals 6 Lucidity trauma and takes 1.3 rounds. After hitting a target with a washable omen, shorten one omen by 2 rounds (attachments first). That target cannot be cleansed again for 4 rounds; this equipment triggers once every 7 game-time units.',
    _ITEM_DEFINITIONS['hospital.hollow_lancet']['description']:
        'Range: 4 cells. Deals 5 Lucidity trauma and takes 1.2 rounds. Load up to 6 units of one liquid from a liquid container; on a hit, inject and consume 1 unit. Injection triggers once every 6 game-time units. The empty lancet can still attack normally.',
    _ITEM_DEFINITIONS['hospital.suture_coil']['description']:
        'After you take trauma, reduce the next trauma by 1 within 6 rounds. Shares this buffer with the Slow-Release Gel Tablet and Glass Rib; trigger interval: 8 game-time units. With the “Connected” meaning, it only affects adjacent targets.',
    _ITEM_DEFINITIONS['hospital.lymph_filter']['description']:
        'At the end of an action, if you have a washable material attachment, shorten one by 2 rounds. After cleansing, no further cleansing can affect you for 4 rounds; trigger interval: 7 game-time units. With the “Pathogen” meaning, it only affects targets marked as pathogens.',
    _ITEM_DEFINITIONS['hospital.cerebral_ampoule']['description']:
        'After you conceive, gain Fluency for 6 rounds and improve natural Imagination recovery. The recovery multiplier is at least 1.25 and uses a higher multiplier when available. A zero base recovery stays at zero; the maximum does not increase. Trigger interval: 7 game-time units.',
    _ITEM_DEFINITIONS['hospital.sterile_glove']['description']:
        'After you take trauma, if you have a washable omen, shorten one by 2 rounds; positive and negative omens both qualify. After cleansing, no further cleansing can affect you for 4 rounds; trigger interval: 7 game-time units. Skill cooldowns remain.',
    _ITEM_DEFINITIONS['hospital.glass_rib']['description']:
        'After you take trauma in a lit position, reduce the next trauma by 1 within 6 rounds. Shares this buffer with the Slow-Release Gel Tablet and Suture Coil; trigger interval: 8 game-time units. Grants no permanent barrier.',
    _ITEM_DEFINITIONS['hospital.pulse_tag']['description']:
        'After you take trauma, emit a brief sound within a 3-cell radius. It triggers at most once per action, with a 7 game-time unit interval.',
    _ITEM_DEFINITIONS['hospital.marrow_spoon']['description']:
        'After consuming an item, if Mind, Lucidity or Imagination actually recovers, restore up to 2 more points of that same attribute without exceeding its maximum. Trigger interval: 8 game-time units; this extra recovery does not trigger recovery effects again.',
    _ITEM_DEFINITIONS['hospital.lumen_mask']['description']:
        'At the end of an action, if your position is lit, reveal disguises within 2 cells and line of sight for 3 rounds. Trigger interval: 7 game-time units. Does not see through walls, reveal the whole map or grant permanent armor.',
    _ITEM_DEFINITIONS['hospital.sealed_ampoule']['description']:
        'Holds up to 6 units of liquid and can be carried back to the Main Dream.',
    _ITEM_DEFINITIONS['hospital.clean_air_bottle']['description']:
        'Holds up to 12 units of gas and can be carried back to the Main Dream.',
    _ITEM_DEFINITIONS['hospital.filter_sac']['description']:
        'A medical supply that can be carried back to the Main Dream.',
    _ITEM_DEFINITIONS['hospital.diagnostic_slide']['description']:
        'A medical supply that can be carried back to the Main Dream.',
    _ITEM_DEFINITIONS['hospital.dream_sensitive']['effect_description']:
        'For 6 rounds, when one attribute recovers, restore up to 3 points of another attribute that is not full. This extra recovery does not trigger this effect again.',
    _ITEM_DEFINITIONS['library.fold']['description']:
        'After moving, mark nearby passages between rooms that can be traversed; it never shows a route through walls.',
    _ITEM_DEFINITIONS['library.card']['description']:
        'When the environment differs from the last recorded state, increase sight range by 1 for 3 rounds. The same state does not extend the effect again.',
    _ITEM_DEFINITIONS['library.testimony']['description']:
        'After a hit, point out a nearby traversable empty cell to consider for a later position. It does not move you or lock onto a target.',
})

EN_REALMS.update({
    '目标：可见失控意识；刻痕保留 3 回合，下次命中时触发一次。':
        'Target a visible Lost Consciousness. The mark lasts 3 rounds and triggers on the next hit.',
    '这项反馈暂不可用：想象力不足、效果仍在冷却，或本回合的触发次数已用完。':
        'This feedback is unavailable: Imagination is too low, the effect is cooling down, or the per-round trigger limit has been reached.',
    '这个位置没有可点燃的材料。': 'There is nothing flammable at this position.',
    '当前没有符合条件的可见目标。': 'There is no visible target that meets the requirements.',
    '附近没有被液体浸湿的敌人。': 'There are no nearby enemies soaked with liquid.',
    '相邻位置没有足够容量接收液体。': 'No adjacent position has enough capacity for the liquid.',
    '封口安瓿碎开，释放了瓶中的液体。': 'The sealed ampoule breaks, releasing the liquid inside.',
    '心智、清醒度或想象力恢复后': 'After Mind, Lucidity or Imagination recovers',
    '没有恢复心智、清醒度或想象力时': 'When Mind, Lucidity and Imagination have not recovered',
    '目标或触发位置有可导电液体时，这条联想才会生效。':
        'This relation works only when conductive liquid is present at the target or trigger position.',
    '从触发位置现有的液体中，最多移动 5 单位到有容量的相邻位置。':
        'Move up to 5 units of existing liquid from the trigger position to an adjacent position with capacity.',
    '对一个被液体浸湿的敌人造成 1 点完整度损伤。':
        'Deal 1 Integrity damage to an enemy soaked with liquid.',
    '在有可燃材料的位置引发一次点燃；初始火焰强度不超过 1，后续燃烧按原有规则进行。':
        'Ignite a position with flammable material once, with initial flame strength up to 1; later burning follows its usual rules.',
    '这项反馈暂不可用：想象力不足、效果仍在冷却，或本回合的触发次数已用完。':
        'This feedback is unavailable: Imagination is too low, the effect is cooling down, or the per-round trigger limit has been reached.',
    '这个位置没有可点燃的材料。': 'There is nothing flammable at this position.',
    '当前没有符合条件的可见目标。': 'There is no visible target that meets the requirements.',
    '附近没有被液体浸湿的敌人。': 'There are no nearby enemies soaked with liquid.',
    '相邻位置没有足够容量接收液体。': 'No adjacent position has enough capacity for the liquid.',
    '封口安瓿碎开，释放了瓶中的液体。': 'The sealed ampoule breaks, releasing the liquid inside.',
    '展开构想后': 'After you conceive',
    '受到创伤后': 'After you take trauma',
    '心智、清醒度或想象力恢复后': 'After Mind, Lucidity or Imagination recovers',
    '没有恢复心智、清醒度或想象力时': 'When Mind, Lucidity and Imagination have not recovered',
    '移动后': 'After moving',
    '命中目标后': 'After hitting a target',
    '摄入物品后': 'After consuming an item',
    '行动结束后': 'At the end of an action',
})


# ---- 2026-10-12 文风批：入口/设施/对白/消息/异象/技能 EN 同步 ----
EN_REALMS.update({
# 入口
'借条上的日期尚未到来。签名处已经有你的笔迹。': 'The due date on the loan slip has not come yet. Your signature is already on it.',
'灯亮起来时，白瓷上的影子都无处藏身。': 'When the lights come on, no shadow can hide on the porcelain.',
'入院单还在等一个名字。': 'The admission form is still waiting for a name.',
# 医院场景：观察描述
'一只浅槽盛着半槽乳白的淋巴液，水面浮着细小的絮。': 'A shallow tray holds milky lymph fluid; fine strands drift on the surface.',
'两只空采样管并排躺着，一管贴蓝绿标签，一管透明。': 'Two empty sample vials lie side by side, one with a blue-green label, one clear.',
'几只封死的气罐立在架上，玻璃后各有一只取液口，刻度还看得清。': 'Sealed gas tanks stand on a rack; each has a tap behind glass, and the gauges are still legible.',
'墙角一扇回风口，灰白的胞尘把格栅糊住了。': 'A return-air vent in the corner; pale spore dust has clogged its grille.',
'这一段的灯全亮着，白光把每条走廊照得发亮。': 'Every lamp on this stretch is on; white light floods each corridor.',
'一只广口瓶盛着浅蓝的洗兆液，瓶口搁着一支玻璃搅拌棒。': 'A wide-mouthed jar of pale-blue wash fluid, a glass stirrer resting on its rim.',
'一张静养椅靠着白墙，安全带叠得整整齐齐。': 'A care chair rests against the white wall, its harness folded neatly.',
'核心停了。无影灯垂在半空，托盘里躺着三件擦净的器械。': 'The core is still. The surgical lamp hangs in mid-air; three polished instruments lie in a tray.',
'一台记录台，屏幕上滚着配液流水。': 'A record desk; its screen scrolls a log of infusion lines.',
'一只没有手的药柜，抽屉自己开了又合。': 'A dispenser with no hands; its drawers open and close on their own.',
'玻璃柜里摆着四件器械，标签一律朝外。': 'Four instruments stand in a glass cabinet, labels facing outward.',
'一只上了封条的药箱，胶带压得平整。': 'A medicine box under sealing tape, pressed flat and even.',
'架上立着一只标着刻度的储液袋，管子垂下来。': 'A graduated fluid bag stands on the rack, its tube hanging down.',
# 医院场景：对白
'淋巴液只伤病原体，不伤人。把它引进槽里、击败它，或沿干路绕行，都算完成观察。': 'Lymph fluid harms pathogens, never people. Lure one in, defeat it or walk the dry route - any of these completes the observation.',
'蓝绿管等着「膜边收缩」的样本，透明管等着「计时缩短」的。封装消耗对应样本各2单位，贴错了可以重贴。': 'The blue-green vial awaits a "membrane contraction" sample; the clear one, a "shortened timing" sample. Sealing costs 2 units of the matching sample; a mismatched label can be redone.',
'端口可以抽取、定量排放，或者留着不动。读一读余量，什么都不消耗。': 'The taps can draw, vent a measured amount, or stay shut. Reading the levels costs nothing at all.',
'排掉胞尘、贴滤膜，或用洗兆液冲一冲，风口都能重新通风。主路上的干路不受这里影响。': 'Vent the dust, fit a filter membrane or rinse it with wash fluid, and the vent breathes again. The main dry route is untouched by this.',
'灯一亮，谁都看得清你。关掉本地灯段后，可以借不透明的侧室藏身；这里只记下这一处路线。': 'When the lamps burn, everyone sees you. Switch off the local lights and hide in the opaque side rooms; only this one route is noted.',
'洗掉一项征兆要花2单位洗兆液；正负面征兆都洗得动。': 'Washing away one portent costs 2 units of wash fluid; positive or negative, both will come clean.',
'在旁边安稳待上三回合，就能用一次。设备只存着一份恢复，不会提高上限。': 'Stay safe beside it for three rounds and it works once. The device holds a single restoration and raises no maximum.',
'三件里只能带走一件：缝合线圈管状态，无垢银剪管材料，白昼面罩管照明。这里和首领奖励共用同一份记录。': 'You may take only one of the three: the suture coil for status, the silver shears for materials, the daylight mask for lighting. This and the boss reward share one record.',
'看守不在了也能读。这里只记观察，不发东西。': 'Readable even without the keeper. It records observations only; it hands out nothing.',
'里面只剩一份药材。配制要花对应的液体2单位和一些心智、清醒度、想象——选项上写得明白。行囊满了就先寄存在旁边的药箱。': 'Only one dose of medicine remains. A preparation costs 2 units of the listed fluid plus some Mind, Lucidity and Imagination - the options say exactly how much. If your bag is full, it waits in the box nearby.',
'四件里挑一件。行囊放不下的话，东西会留在柜旁等你。': 'Pick one of the four. If your bag cannot hold it, it will wait beside the cabinet.',
'箱里封着三份药。开箱只此一次，没拿走的会一直留在这里。': 'Three doses are sealed inside. The box opens once; whatever you leave stays here for good.',
'袋里还剩12单位，倒完就没了。装不下的部分会留在袋里。': 'The bag holds 12 units; when it runs out, it is out. What your containers cannot hold stays in the bag.',
# 医院消息
'容器里的{material}还差2单位。': 'You are 2 units of {material} short.',
'心智、清醒度或想象力不够。': 'Not enough Mind, Lucidity or Imagination.',
'这里的奖励已经领过了；记录仍可阅读。': 'The reward here has already been taken; the records remain readable.',
'没有装得下的容器；储液没有动。': 'No container with room; nothing was drawn.',
'{name}：{done}': '{name}: {done}',
'样本封进了载管。': 'The sample is sealed in the vial.',
'标签贴好，样本封存。': 'Label affixed; sample sealed.',
'药片在托盘里落定。': 'The tablet settles into the tray.',
'你取走了那件器械。': 'You take the instrument.',
'你靠着静养椅歇了一回。': 'You rest a while in the care chair.',
'你取走了药物。': 'You take the medicines.',
'回风口重新通风了。': 'The return-air duct breathes again.',
'灯段熄灭了。': 'The lights go out.',
'你取走了容器。': 'You take the containers.',
'药品收进了行囊。': 'The medicine goes into your bag.',
'灯段重新亮了起来。': 'The lights come back on.',
'它守着你歇了一回。': 'It stands guard while you rest.',
'基础容器已经拿过了。': 'You already took the basic containers.',
'准备盒已经空了。': 'The prep box is already empty.',
# 选项 label（清洗）
'用洗兆液洗短一项并选洗忆泡腾片': 'Wash one portent shorter with wash fluid, then choose a Memory-Wash Tablet',
'用洗兆液洗短一项并选晨醒含片': 'Wash one portent shorter with wash fluid, then choose a Morning-Wake Lozenge',
# NPC 对白
'「分诊吗？」铃舌晃了一下，没有等到回音。「这里没人挂号。要容器的话，自己拿一只。」': '"Triage?" The bell clapper swings, but no answer comes. "Nobody queues here. If you need a container, take one."',
'「只剩最后一份药材。」抽屉自己开出一条缝。「处方带来了吗？」': '"Only one dose of medicine left." A drawer opens a crack by itself. "Did you bring the prescription?"',
'「先帮我把回风口清干净。」它停稳了，白布抖平一角。「之后我替你守一会儿这儿。」': '"Clear the return-air vent for me first." It steadies itself and smooths a corner of white cloth. "After that I will keep watch here for a while."',
'「阀门别乱拧，供液就那么些。」它举了举手里空了一半的滴瓶。「灯的开关归你管。我不在了，记录还在。」': '"Do not fiddle with the valves; the supply is nearly done." It lifts the half-empty drip bottle in its grip. "The lamp switches are yours to mind. When I am gone, the records stay."',
# 医院异象 12 条
'薄膜裹着一滴安静的液体，边缘却一直颤动。它碰到你便缩回一格。': 'A film wraps a drop of quiet liquid, its edge always trembling. When it touches you, it retreats one cell.',
'透明衣壳像细小针尖排列。它射出针线前，地板会先留下一道提示。': 'A transparent capsid lined with needle tips. Before it fires its thread, the floor shows a mark first.',
'一簇洁白孢芽，像没有开封的培养样本。': 'A cluster of white spore buds, like an unopened culture sample.',
'菌丝束沿地板接缝舒展，像误写在白瓷上的缝线。': 'A bundle of hypha spreads along the floor seams, like sutures miswritten on porcelain.',
'细长器械自行滑行，针尖总比身体先转向。': 'A slender instrument glides on its own; the needle tip always turns before the body.',
'一对没有手握住的钳口，在空中轻轻开合。': 'A pair of forceps with no hand to hold them, opening and closing gently in the air.',
'金属听诊盘浮在一条看不见的软管末端。': 'A metal stethoscope disc floats at the end of an unseen tube.',
'银架推着最后几滴浅蓝配液，滴管里的液面已经很低。': 'A silver stand pushes the last drops of pale-blue mixture; the level in its dripper has run low.',
'培养皿般的圆冠悬在病原体上方，边缘垂着灰白的絮。': 'A petri-dish crown hovers above the pathogen, greyish wisps hanging from its rim.',
'三枚刀片在洁净圆盘上轮换着反光。': 'Three blades take turns catching the light on a clean disc.',
'一圈过亮的扫描镜缓慢旋转，白光扫过之处连影子都藏不住。': 'An overbright scanner ring rotates slowly; where its white light sweeps, even shadows give themselves away.',
'银白环状灭菌设备包着透明核心。它相信清除所有变化就能永远安全。': 'A silver-white sterilizer ring encloses a transparent core. It believes that removing all change makes it safe forever.',
# 医院技能 14 条
'射出至多五格的针线，命中一次清醒创伤6；实体墙会截断针线。': 'Fires a needle thread of up to 5 cells, dealing 6 Lucidity trauma once; solid walls cut the thread.',
'抖出胞尘：孢芽团每次4单位、分至多两格，孢子冠每次6单位、分至多四格；一场至多抖出12单位。': 'Shakes out spore dust: buds shed 4 units across at most 2 cells, the crown sheds 6 across at most 4; no more than 12 units in one encounter.',
'在目标附近布下至多两格菌丝迟线；踩中的目标拖上两回合迟拍。': 'Lays a delayed hypha line of at most 2 cells near the target; those who tread it slow for two rounds.',
'沿直线推进至多两格，撞上实体便停；警示线上的目标吃一次清醒创伤7。': 'Dashes up to 2 cells along a straight line, stopping at anything solid; targets on the warning line take 7 Lucidity trauma once.',
'预告之后，把仍留在短线上的目标拖近一格；拖不进墙，也不挤进已有人的格子。': 'After the warning, drags a target still on its short line one cell closer; never into walls, nor into an occupied cell.',
'把它最后一次看清的位置广播给同伴；广播之后不再更新。': 'Broadcasts the last position it saw clearly to its peers; the report never updates afterwards.',
'往至多三格滴下共2单位脑脊液；一场至多滴6单位。': 'Drips 2 units of cerebral fluid across at most 3 cells; no more than 6 units in one encounter.',
'给自己裹上三回合菌膜；替它挡下一次命中的1点创伤。菌膜可以洗掉。': 'Wraps itself in a membrane for three rounds, absorbing 1 trauma from the next hit. The membrane can be washed away.',
'沿目标附近三格扫出一道弧，命中一次清醒创伤10；扫完至少停一回合。': 'Sweeps an arc across 3 cells near the target, dealing 10 Lucidity trauma once, then pauses for at least a round.',
'射出至多六格扫描线，命中清醒创伤9；它自己周围半径2被照亮，三回合后恢复。': 'Fires a scan line of up to 6 cells, dealing 9 Lucidity trauma; its own surroundings light up within radius 2 and recover after three rounds.',
'锁定至多七格细线，落线时命中一次清醒创伤9。': 'Locks a thin line of up to 7 cells, dealing 9 Lucidity trauma once the line falls.',
'预告两回合后，在周围八格扬起一圈稀疏水环；敌我的一项可洗征兆被缩短3，并受心智创伤5。': 'After a two-round warning, raises a sparse ring of water across the surrounding 8 cells; one washable portent on either side shortens by 3, with 5 Mind trauma.',
'往首次确定的至多三个槽格注液，每次6单位、总量12；流出的脑脊液对敌我都有帮助。': 'Fills at most 3 fixed basin cells chosen at the start, 6 units each and 12 in all; the cerebral fluid that flows out helps both sides.',
'第二阶段起，预告两回合后召出一只膜泡球（完整度6、清醒创伤3）；至多两次，同时至多一只，膜泡没有溶解奖励。': 'From its second phase, warns for two rounds then summons a membrane bubble (6 integrity, 3 Lucidity trauma); at most twice, one at a time, and the bubble yields no dissolution reward.',
})

# ---- 藏书宫：respond 消息 / 异象介绍 / 十五技能 EN ----
EN_REALMS.update({
'随便看，不要钱；复位随时可做。': 'Look freely; it costs nothing. A reset is always available.',
'索引柜目前页码为{pages}；相邻两页可交换，正序会指出收藏位置。': 'The index cabinet\'s current page order is {pages}. Swap adjacent pages; the correct order reveals the collection location.',
'两组书稿目前为{drafts}；并置后它们会按同一阅读次序排列。': 'The two drafts currently read {drafts}; collated, they follow one reading order.',
'目录和两份页码可以互相对照。': 'The catalogue and both sets of page numbers can be compared.',
'页码回到初始位置。': 'The page numbers return to their starting places.',
'目录指出了一条干燥回廊；想象力也补回来两点。': 'The catalogue points out a dry gallery, and 2 points of Imagination come back with it.',
'这一次的借阅名额已经用掉了。': 'This cabinet\'s single loan has already been used.',
'行囊放不下；借阅名额还留着。': 'Your bag cannot hold it; the loan is still reserved for you.',
'你把{name}借走了。': 'You borrowed {name}.',
'返程目录台摊开着一册目录，最后一页夹着你的借阅记录。': 'The return desk lies open to a catalogue; your loan record rests in its last page.',
'回去的路一直通着。这里的书架、材料和已借出的东西都留在原处。': 'The way back stays open. The shelves, materials and everything you borrowed remain where they are.',
'一排黄铜开关嵌在木台里，标着本层各盏阅读灯的位置。': 'A row of brass switches set into a wooden desk, marking each reading lamp on this floor.',
'开关对两边的眼睛一视同仁。拨一下花一行动；地上的东西不受影响。': 'The switches treat both sides\' eyes alike. One flip costs one action; nothing on the floor is disturbed.',
'台面上的机关积着薄灰，看起来很久没人动过。': 'A thin layer of dust covers the desktop contraption; no one has touched it in a long while.',
'誊本台摊着一部厚得反常的目录，纸页边缘全是空着的条目栏。': 'The fair-copy desk lies open to an unnaturally thick catalogue, every entry column along its pages still blank.',
'未尽目录问：你愿意接受唯一、永久正确的定义吗？': 'The Unfinished Catalogue asks: will you accept the one, permanent, correct definition?',
'只是读一读，它不会动怒。一旦应战，各条回廊都能避开它的索引线。': 'It does not anger at mere reading. Once the fight begins, every gallery can skirt its index lines.',
'藏品柜的玻璃擦得很亮，四件小东西各占一格。': 'The cabinet glass is polished bright; four small things each occupy a cell.',
'只能借走一件。中途换主意不算违约，想换别的也还来得及。': 'You may borrow only one. Changing your mind midway breaks no rule; there is still time to choose differently.',
# 藏书宫十二异象
'它捧着一本谁都没借过的书，目光越过书页追着你看。': 'It holds a book no one has ever borrowed, its gaze following you over the pages.',
'它在一道看不见的门槛前来回踱步，等谁先迈过去。': 'It paces before an invisible threshold, waiting for someone to step across first.',
'一页页码印反了，墨从字的背面渗出来。': 'A page number printed backwards, ink seeping through from the far side of the characters.',
'它讲到一半就停笔，剩下的话被擦得只剩一道白痕。': 'It stops writing midway through a sentence; the rest has been erased to a single pale streak.',
'索引慢了半拍，才翻到你所在的那一页。': 'The index turns to your page half a beat too late.',
'它提着一盏借来的灯；光走到哪儿，哪儿就欠它一回。': 'It carries a borrowed lamp; wherever the light goes, it leaves a debt behind.',
'它走过的地方，书页似的地面留下一道折痕。': 'Wherever it walks, the page-like floor keeps a crease.',
'它抱着一摞永远装订不完的散页，走到哪儿收到哪儿。': 'It hugs an armful of loose pages it can never finish binding, collecting more wherever it goes.',
'它抄写一切，唯独不抄自己；笔下只落下划线和校订的记号。': 'It copies everything but itself; its pen sets down only struck lines and proofreader marks.',
'同一件事，它能誊出好几个互相出入的版本。': 'Of the same event it can transcribe several versions that disagree with each other.',
'它递来的稿纸上全是空白——它拒绝誊清任何一个字。': 'The manuscript it hands over is entirely blank - it refuses to make a fair copy of a single word.',
'一部永远差最后一页的目录。它的条目都空着，等你被写进去。': 'A catalogue forever missing its final page. Every entry stands empty, waiting for you to be written in.',
# 藏书宫十五技能
'沿直线追问至多四格，命中一次心智创伤5；起笔之后落点固定，不再跟着你转向。': 'Pursues along a straight line of up to 4 cells, dealing 5 Mind trauma once; once the stroke starts, its mark is fixed and no longer follows you.',
'目标在视线内，且两人之间有可以落笔的直线。': 'The target is in sight, and a straight line lies between you for the stroke to follow.',
'横移出线，或用实体遮挡。': 'Step out of the line, or block it with something solid.',
'把两格内一扇还开着的门带上，两回合后它自己重新敞开。': 'Pulls shut a still-open door within 2 cells; it swings open again by itself after two rounds.',
'两格内有一扇空置的门。': 'An unoccupied door stands within 2 cells.',
'门只在侧廊上；等它自己敞开。': 'The door hangs only on a side gallery; wait for it to open again.',
'把你此刻站着的格子泼成墨迹，停留三回合；墨里行走会拖沓。': 'Splashes the cell you stand on into an inkstain that lasts three rounds; walking through ink drags.',
'目标可见。': 'The target is visible.',
'别停在原地；墨迹过几拍就干了。': 'Do not stand still; the ink dries after a few beats.',
'把自己身上的一项负面征兆整个省略掉，像删去一个多余的词。': 'Omits one negative portent from itself entirely, like striking out a needless word.',
'它身上确有负面征兆。': 'It truly carries a negative portent.',
'省略掉的就是没有了。': 'What is omitted is simply gone.',
'翻回它上一处站过的位置，像书签跳回上一回目。': 'Flips back to where it last stood, like a bookmark returning to an earlier chapter.',
'上一处位置在三格以内，且仍然空着。': 'Its previous position lies within 3 cells and is still empty.',
'占住它回来的位置。': 'Take the place it would return to.',
'把四格内一盏阅读灯的光借走两回合；光跟着它走，原处暗下去。': 'Borrows the light of a reading lamp within 4 cells for two rounds; the light goes with it, and the old spot darkens.',
'四格内有一盏阅读灯。': 'A reading lamp stands within 4 cells.',
'灯最终会归还原位。': 'The lamp returns to its place in the end.',
'折过一页书：挪进三格内一扇挨着书架的空格。': 'Turns a page of the book: slips into an empty cell beside a bookshelf within 3 cells.',
'三格内有一格空地挨着书架。': 'An empty cell next to a bookshelf lies within 3 cells.',
'把书架旁的空地占住。': 'Occupy the open ground beside the shelves.',
'收走身旁一叠干纸替自己压上纸护，两回合内你打它会更轻；纸堆会薄下去。': 'Takes a stack of dry paper beside it to press into a paper ward; for two rounds your blows land lighter, and the stack grows thinner.',
'身旁有还没烧完的干纸堆，且它身上还没有纸护。': 'An unburnt dry-paper stack stands beside it, and it holds no paper ward yet.',
'抢先烧掉纸堆，或等纸护耗尽。': 'Burn the paper stack first, or wait out the ward.',
'沿直线划出至多六格的长线，命中一次心智创伤6。': 'Draws a long line of up to 6 cells, dealing 6 Mind trauma once.',
'替四格内的一名同伴校订一遍，压上两回合的纸护。这场里它只做一次。': 'Proofreads one ally within 4 cells, pressing a paper ward onto them for two rounds. It does this only once per encounter.',
'四格内有还没拿到纸护的同伴。': 'An ally without a paper ward stands within 4 cells.',
'同伴的纸护只能挡一下。': 'An ally\'s paper ward stops only one blow.',
'把自己誊出几个互相出入的版本：身旁空格里最多多出两份单薄的誊影，各撑八回合。': 'Transcribes itself into disagreeing versions: at most two thin echoes appear in adjacent empty cells, each lasting eight rounds.',
'身旁有空格，且连同誊影在内还不足两份。': 'An empty cell stands beside it, and it and its echoes number fewer than two.',
'誊影只有一层纸厚。': 'An echo is only one sheet of paper thick.',
'把身旁至多两格抹成空白，停留两回合；空白里落不下别的把戏。': 'Blanks out up to 2 adjacent cells for two rounds; no other trick can land inside the blank.',
'身旁有空格。': 'An empty cell stands beside it.',
'空白不挡路，只是什么都留不住。': 'The blank blocks no path; it simply holds nothing.',
'沿直线归出至多七格的目录长线，命中一次心智创伤7；被线穿过的目标眼前会发花。': 'Runs a catalogue line of up to 7 cells, dealing 7 Mind trauma once; anyone the line passes through finds their vision blurring.',
'把你周围的格子涂掉至多两格，墨迹停留三回合；正中的主廊不涂。': 'Blots out up to 2 cells around you with ink that lasts three rounds; the central gallery stays clean.',
'主廊上没有墨。': 'No ink lands on the central gallery.',
'落下至多七格的最后一页：先写前半行，等你行动之后，后半行跟着落下；每半行各带一次心智创伤7。': 'Sets down a final page of up to 7 cells: the first half-line falls now, and after you act the second follows; each half carries 7 Mind trauma once.',
'后半行只认预告的格子。': 'The second half-line lands only on the cells it announced.',
})

# 主梦异象 3 条 + 物品/技能杂项
EN_REALMS.update({
'由反复折叠的纸页聚成，会沿可辨认的边缘追逐声音。': 'Gathered from paper folded again and again, it chases sound along any edge it can make out.',
'一扇会自行游荡的门，门缝里还在小声转述它看见的东西。': 'A door that wanders on its own, still whispering reports of what it has seen through its crack.',
'一只沉甸甸的墨水瓶，瓶口渗出的墨在地面洇开，不肯干。': 'A heavy ink bottle; the ink seeping from its mouth spreads across the floor and refuses to dry.',
})


# ---- 文风批 EN 补遗：物品原始描述 / 征兆 / UI 模板 ----
EN_REALMS.update({
# 藏书宫八件原始描述
'跨过门后，下一次攻击多一分力；六次行动内有效。': 'Cross a door and your next strike lands a little harder, for six actions.',
'再遇见它时，记下它此刻的方位与完整度；六次行动内离开视野也不更新，不揭示全图。':
 "Meet it again and it records the target's position and integrity; if that target leaves your sight within six actions the record stops updating. It reveals no map.",
'走完一步，折出已探索区域通向未知的最近两处边界；只说边界，不记那边有什么。':
 'After a step, it folds out the two nearest boundaries where the explored area meets the unknown; it names the boundary only and never records what lies beyond.',
'四周没人时，下一次自然恢复多回来一点；总上限不变。': 'When no one is near, your next natural recovery returns a little more; the cap is unchanged.',
'命中后，把目标周围一格的导电与火源连接定住三回合；伤害不复制。':
 'On a hit, it pins the conductive and fire-source connections within one cell of the target for three rounds; damage is never copied.',
'拒绝一次弱控制；十次行动一回，直接创伤不挡。': 'Refuses one weak control, once every ten actions; it does not stop direct trauma.',
'环境状态与上次记录不同时，视野增加2格，持续4回合；每6次行动至多记一次。':
 'When the surroundings differ from your last record, sight range grows by 2 for four rounds; at most once per 6 actions.',
'命中后记下这个目标：下次打它时，先报出它被推开几格、撞在哪里。':
 'On a hit it remembers the target: your next shot at it first reports how far it will be pushed and what it will strike. It changes nothing by itself.',
# 主梦物品（宣传词清理）
'崩解度获取 +4，越攒越厚。': 'Dissolution gain +4; it piles up as you go.',
'戴着它，攻击耗时 −0.1。': 'Worn, your attacks take 0.1 less time.',
'徒手操作机关与电线不再触发反噬。': 'Working mechanisms and wires barehanded no longer bites back.',
'把一句未说完的话压成直线弹体射出去。': 'Compresses an unfinished sentence into a straight shot and fires it.',
'机箱前面板上的亚克力小水晶。晃一晃，静电都绕着走（心智与清醒的伤口都浅一点）。': 'An acrylic trinket from a case front. Give it a shake and static walks around you (Mind and Lucidity wounds run a little shallower).',
# 医院十件原始描述（新 key）
'一柄不肯合拢的手术剪。近战耗时1.3回合，一次清醒创伤6；命中后可把目标一项可清洗征兆洗短2回合（先洗附着，同一目标净化后4回合内不再受洗）。洗征兆每7点游戏时间至多一次。': 'Surgical shears that refuse to close. Melee in 1.3 rounds, 6 Lucidity trauma once; on a hit it may shorten one washable portent of the target by 2 rounds (attachments first; the same target resists washing for 4 rounds afterwards). Washing at most once per 7 game-time.',
'一支空心的注射针。射程4格，耗时1.2回合，一次清醒创伤5；能从液体容器灌入一种液体（至多6单位），命中后注入并耗掉1单位。注入每6点游戏时间至多一次；针空着时仍可普通攻击。': 'A hollow lance. Range 4, 1.2 rounds, 5 Lucidity trauma once; it can load one fluid from a container (up to 6 units) and injects 1 unit on a hit, spending it. Injection at most once per 6 game-time; an empty lance still attacks.',
'一卷缝合线圈。挨了创伤后，6回合内替你抵掉下一次创伤的1点。这份缓冲与缓释凝片、玻璃肋共用；每8点游戏时间至多起效一次。搭配「相接」词义时，只护住相邻的目标。': 'A suture coil. After you take trauma, it absorbs 1 point of the next hit for 6 rounds. This buffer is shared with Slow-Release Gel and the Glass Rib, at most once per 8 game-time. With the Adjacent reading, it guards only adjacent targets.',
'一枚淋巴滤环。行动结束后，若你身上有可清洗的材料附着，替你把其中一项洗短2回合；净化后4回合内同一目标不再受洗。每7点游戏时间至多一次。搭配「病原体」词义时，只滤带病原体标记的目标。': 'A lymph filter ring. At the end of an action, if washable material clings to you, it shortens one by 2 rounds; a cleansed target resists for 4 rounds. At most once per 7 game-time. With the Pathogen reading, it filters only pathogen-tagged targets.',
'一只脑脊安瓿。展开构想后，获得6回合的流畅：想象力的自然恢复至少提速到1.25倍（与更高倍率取高）。基础恢复为0时不会凭空多出恢复，也不抬高上限。每7点游戏时间至多展开一次。': 'A cerebral ampoule. After you conceive, fluency flows for 6 rounds: natural Imagination recovery runs at least 1.25 times (the higher multiplier wins). Zero base recovery stays zero, and maxima never rise. At most once per 7 game-time.',
'一只无垢手套。受到创伤后，把你身上一项可清洗征兆洗短2回合，正面负面都行；净化后4回合内不再重复。每7点游戏时间至多一次，也不影响技能冷却。': 'An immaculate glove. After you take trauma, it shortens one washable portent of yours by 2 rounds, positive or negative; a cleansed target resists for 4 rounds. At most once per 7 game-time, and it never touches skill cooldowns.',
'一根玻璃肋。在有光的位置挨了创伤后，6回合内替你抵掉下一次创伤的1点；与缓释凝片、缝合线圈共用这一份缓冲，每8点游戏时间至多一次。它不是永久的屏障。': 'A glass rib. Take trauma while standing in light and it absorbs 1 point of the next hit for 6 rounds; shared with Slow-Release Gel and the Suture Coil, at most once per 8 game-time. It is no permanent shield.',
'一枚心搏标签。受到创伤后发出半径3格的短促声响；一次行动至多响一次，间隔7点游戏时间。': 'A pulse tag. When you take trauma it chirps across radius 3; at most once per action, with a 7 game-time gap.',
'一把骨髓银匙。摄入物品后，若心智、清醒度或想象力确实恢复了，对应指标再额外恢复至多2点，不超上限；这份额外恢复不会再触发连锁。每8点游戏时间至多一次。': 'A marrow spoon. After you ingest something that truly restored Mind, Lucidity or Imagination, the same stat recovers up to 2 more, never past its cap; the bonus triggers nothing further. At most once per 8 game-time.',
'一张白昼面罩。行动结束时若你正站在光里，照出半径2格内且视线可达的伪装，持续3回合。每7点游戏时间至多一次；它不透墙，也不揭示全图。': 'A daylight mask. End an action while standing in light and it exposes disguises within radius 2 and in sight for 3 rounds. At most once per 7 game-time; it sees through no walls and reveals no map.',
# 征兆（月下 / 夜皇后的幽光）
'流动月光替你照亮四周：视野 +4。': 'Flowing moonlight lights your surroundings: vision +4.',
'夜皇后的幽光替你照亮四周：视野 +4。': 'The Night Queen\'s ghost-light lights your surroundings: vision +4.',
# UI 模板
'这里放不下 {item}：{area} 格的形状和现有摆放冲突，先挪开或拆掉一些实体再试。': 'No room for {item} here: its {area}-cell shape clashes with the current layout. Move or clear some solid pieces first.',
'成功反馈：想象 1 · 同类反馈冷却 6 回合': 'Successful response: 1 imagination; shared family cooldown 6 turns',
'借助锋利刀锋，': 'With a sharp edge, ',
})

EN_REALMS.update({
'每个留白续写件只按自己那份次级强度生效；按实际经过的回合回流，合计额外回流每回合最多 3 点。': 'Each Blank Edge piece works only by its own secondary strength; regeneration follows elapsed rounds, with at most 3 extra Imagination per round in total.',
})

EN_REALMS.update({
'只在这对端点之间折：落到对端最近的一格空地上，找不到空地就不收这一笔。敌人照样走完它们的那一拍。': 'Fold only between this pair of endpoints: you land on the nearest open cell at the far end, and if none exists the fold costs nothing. Enemies still finish their beats.',
'联想盘上放不下 {item}。': 'The board has no room for {item}.',
})

EN_REALMS.update({
# ── 图书馆 NPC 学识问答（2026-10-12 内容批）──
'请教这座宫的物件': 'Ask about the palace furnishings',
'再问一句': 'One more question',
'胡桃木书架挡视线也挡直线，最怕火；烧穿了，视线和弹道都跟着改道。': 'Walnut shelves block sight and straight shots, and fear fire above all; burn one through and sightlines and trajectories all reroute.',
'推书车挪一下，遮挡跟着挪；借它打掩护，别把自己堵死。': 'Nudge a book cart and the cover moves with it; use it for shelter, but do not wall yourself in.',
'错页索引柜的页码能对调；正序排好，它才肯指出收藏的位置。': 'The misprinted index cabinet lets you swap page numbers; only when they read in order will it point out where things are kept.',
'湿墨只泼在侧路上，踩了会导电；横着走索引廊，遇不上长线。': 'Wet ink splashes only on the side paths and conducts if you step in it; walk the index gallery crosswise and no long line will reach you.',
'同一座庭院开着一排不同的窗口；换一扇窗，看到的规矩就不一样。': 'One courtyard opens onto a row of different windows; change the window and the rules you see change with it.',
'黄铜阅读灯对谁都亮，敌我都算；灯体不结实，别指望它替你挡刀。': 'Brass reading lamps shine for everyone, friend and foe alike; the lamp bodies are fragile, so do not expect them to block a blade.',
'干纸堆是燃料，烧完就变回普通地面；防火书柱和防火石面烧不着，退路可以选它们。': 'Dry paper stacks are fuel; burned out, they revert to ordinary floor. Fireproof pillars and stone paving cannot burn, so pick those for a retreat.',
'双声校勘台纯属自愿；并置两组书稿，它们会按同一阅读次序排好，给你指一条干燥回廊。': 'The collation desk is entirely voluntary; set two manuscripts side by side and they order themselves to one reading, pointing out a dry corridor.',
'三份矛盾记录说的是同一件事的三个版本；都记下来，未尽目录才会认真听你说话。': 'The three contradictory records tell one event in three versions; note them all and the Unfinished Catalogue will finally take you seriously.',
'回应未尽目录就会开战。读记录不花钱；想清楚了，再去按确认。': 'Answering the Unfinished Catalogue starts the fight. Reading the records costs nothing; think it through before you confirm.',
# ── 图书馆散落事件 ──
'旧借书卡': 'An old borrowing card',
'一张泛黄的借书卡插在书目缝里，借阅人一栏只剩半个名字。': 'A yellowed borrowing card tucked in the catalogue seam; the borrower line holds half a name.',
'读卡面残字': 'Read the torn name',
'放回去': 'Put it back',
'借阅人：——（被撕去）。归还日期写的是「借阅之门打开之前」。': 'Borrower: ——(torn away). The due date reads "before the Gate of Loans opened".',
'借阅人栏是一片晕开的墨。备注：本人已随第七次修订合并。': 'The borrower line is a blot of ink. Note: subject has been merged with the seventh revision.',
'借阅人只画了一扇窗。管理员的批注：人不在，窗口照常开放。': 'The borrower drew only a window. Librarian\'s note: absent, but the window remains open.',
'四行笔迹互相涂改，每一行都声称前一行是抄错的自己。': 'Four lines of handwriting correct one another; each claims the line above is a mis-copied self.',
'借阅人栏空着。背面一行小字：目录未完成，姓名暂缺。': 'The borrower line is empty. On the back, small: catalogue unfinished, name pending.',
'残名让你想起自己的名字也是一点点拼回来的；想象力补回一点。': 'The torn name reminds you your own was pieced together bit by bit; Imagination +1.',
'这张卡你已经读过；只剩半个名字。': 'You have read this card already; only half a name remains.',
'写满批注的桌角': 'A desk corner full of marginalia',
'桌角压着半册旧批注，页边写满不同笔迹。': 'Half a notebook of old annotations weighs down the desk corner, margins crowded with different hands.',
'顺着批注想一会儿': 'Ponder the marginalia',
'擦掉批注': 'Erase the marginalia',
'合上': 'Close the notebook',
'页边写着：「外墙不是墙，是还没写完的封面。」': 'In the margin: "The outer wall is not a wall — it is a cover still being written."',
'「页码乱了不要紧，要紧的是有人肯把它们排回去。」': '"Scrambled pages matter little; what matters is someone willing to put them back in order."',
'「窗换了一扇，看见的庭院就换了一座——庭院其实没动。」': '"Change the window and you change the courtyard — the courtyard itself never moved."',
'「声音分开存放，才吵不起来；吵起来的都进了同一页。」': '"Voices kept apart never quarrel; the quarrelling ones all ended up on the same page."',
'「最后一册永远写不完。写完的那天，就没有下一页了。」': '"The final volume is never finished. The day it is, there is no next page."',
'批注替你把没说清的事说清了；清醒补回一点。': 'The marginalia says clearly what you could not; Lucidity +1.',
'这条批注你已经读过；页边只剩熟悉的笔迹。': 'You have read this marginalia already; only the familiar hand remains.',
'你把批注擦干净了。桌面露出原来的木色，谁的观点都没留下。': 'You wipe the margin clean. The desk shows its plain wood; no one\'s opinion remains.',
# ── 医院散落事件 ──
'散落的病历夹': 'A dropped medical chart',
'一只病历夹掉在推车旁，纸页散开，夹子还咬着最后一页。': 'A chart has fallen beside the cart, pages fanned out, the clip still biting the last sheet.',
'读一遍病历': 'Read the chart',
'「入院原因：不肯醒来。处置：继续观察。」': '"Admitted for: refusing to wake. Treatment: continued observation."',
'「处方栏写着：每天少想一点。签名被划掉过三次。」': 'The prescription reads: "Think a little less each day." The signature has been struck through three times.',
'「病历记录：患者坚称自己是别人写的批注。结论：无异常。」': 'Chart entry: patient insists they are someone else\'s marginal note. Conclusion: no abnormality.',
'「护理记录：白昼延长了四小时，患者要求关灯，被驳回。」': 'Nursing log: daylight extended four hours; patient requested lights out; request denied.',
'「最后一页：患者痊愈。痊愈的定义由本院保留。」': 'Final page: patient recovered. The definition of recovery is retained by this institution.',
'停摆的叫号屏': 'A stalled queue screen',
'叫号屏斜挂在墙上，一半亮着，号码停了很久。': 'A queue screen hangs askew on the wall, half lit, its number long frozen.',
'看一眼最后的号码': 'Check the last number',
'叫号屏停在 077。下面一行小字：请 078 号自行入梦。': 'The screen holds at 077. Beneath, small: "No. 078, please proceed to dream on your own."',
'屏幕滚动着：现在的号码是——闪了闪——还是刚才那个。': 'The screen scrolls: "Now serving—" it flickers "—still the one before."',
'屏上只有一句：请叫到名字的就诊者不要回应。': 'The screen shows a single line: "When your name is called, do not answer."',
'叫号屏排着一长串「无」，偶尔夹一个被划掉的名字。': 'The queue lists a long string of "none", with the occasional struck-out name between.',
'屏幕黑了一半，剩下半边写着：本日全部就诊完毕。': 'Half the screen has gone dark; the rest reads: "All consultations concluded for today."',
'病历读完了。': 'Finished reading the chart.',
'号码看清楚了。': 'The number is clear now.',
})

# Messages generated by portable library conceptions.
EN_REALMS.update({
    "书页翻过去了，空白仍是空白。": "The page turns, leaving the blank unchanged.",
    "你沿折痕跨到了另一侧。": "You step along the fold to the other side.",
    "书签夹住了脚下这一页。": "Your bookmark holds this page beneath your feet.",
    "你回到了夹着书签的地方。": "You return to your bookmarked place.",
    "你收起了脚下的书签。": "You remove the bookmark beneath your feet.",
    "书签那一页被压住了；它还留在那里。": "The bookmarked place is blocked; the bookmark stays there.",
    "墨线掠过眼睛，目光暗下去了。": "Ink crosses their eyes, dimming their sight.",
    "那处薄障被划掉了，后面露出空地。": "The thin barrier is struck out, revealing open ground.",
    "页边合拢，夹住了它的脚步。": "The page margins close around its feet.",
    "页边合拢时，它已经挣脱了。": "It slips free as the page margins close.",
    "旁注沿方向补出 {learned} 格地形轮廓（长 {length}、宽 3）；只标开放与阻挡。": "Margin Note traces {learned} terrain cells in this direction ({length} long, 3 wide), showing only open or blocked ground."
})

# 2026-10-22（P3）：图书馆信息装——索引的六次行动记录、透镜的连接预览、
# 残页的推离预演。旧三条（只报完整度／只列邻格）保留在上面，勿删。
EN_REALMS.update({
    '失时索引还记着{name}：上次见到是在 {cell}，当时完整度 {integrity}（记录余 {turns} 次行动）。':
        'The Index of Lost Time still remembers {name}: last seen at {cell} with Integrity {integrity} ({turns} actions left on the record).',
    '失时索引记下{name}：此刻在 {cell}，完整度 {integrity}；六次行动内它离开视野，这条记录也不再更新。':
        'The Index of Lost Time records {name}: now at {cell}, Integrity {integrity}. If it leaves your sight within six actions the record stops updating.',
    '阿莱夫透镜定住{name}周围三回合：导电 {wires} 处、火源 {fires} 处（{cells}）。':
        'The Aleph Lens pins the area around {name} for three rounds: {wires} conductive and {fires} fire-source cells ({cells}).',
    '阿莱夫透镜照过去：{name}周围一格没有可见的导电或火源连接。':
        'The Aleph Lens finds no visible conductive or fire-source connection around {name}.',
    '罗生门残页留了另一种写法：下次打{name}时，会先报出它被推开几格、撞在哪里。':
        'The Rashomon Fragment keeps another wording: the next hit on {name} will first report how far it is pushed and what it strikes.',
    '残页先演了一遍：这一击把它推开 {moved} 格，{stop}，停在 {cell}。':
        'The fragment plays it out first: this hit pushes it {moved} cells, {stop}, ending at {cell}.',
    '残页先演了一遍：这一击把它推开 {moved} 格，停在 {cell}，一路没撞到东西。':
        'The fragment plays it out first: this hit pushes it {moved} cells and ends at {cell}, striking nothing on the way.',
    '撞上{thing}': 'strikes {thing}',
    '撞上另一个意识': 'strikes another mind',
    '推出边缘': 'is pushed off the edge',
})
