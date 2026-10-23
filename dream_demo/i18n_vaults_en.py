"""Authored vault scenes, named circuit ports and actionable maintenance clues."""
EN_VAULTS = {
    '回路检修员':'Circuit technician',
    '先看输入，再看它们怎样汇入输出。交叉的线路有绝缘，不会因为靠在一起就通电。':
        'Start with the inputs, then follow them to the output. Crossing traces are insulated; touching on the map does not connect them.',
    '询问这张回路的检修顺序':'Ask how to service this circuit',
    '怎么看输入状态？':'How do I read the inputs?',
    '查看机关可以读到输入名称、通断和摆轮相位。开关靠近后操作，压板要踩上去。':
        'Inspect components to read input names, power states and clock phases. Operate switches from nearby; step onto plates.',
    '先观察输入与输出之间的线路。':'Follow the traces between the inputs and outputs.',
    '电源开关':'Power switch','通路校验':'Path verification','维护旁路':'Service bypass',
    '旁路反相':'Bypass inverter','终段校验':'Final verification','储藏门':'Storage gate',
    '状态显影':'Status display','基准摆轮':'Reference clock','调相摆轮':'Adjustable clock',
    '相位接线':'Phase relay','一号压板':'Plate one','二号压板':'Plate two','三号压板':'Plate three',
    '音序寄存':'Melody register','校验使能':'Verification enable','灌注区感应':'Delivery-bay sensor',
    '供水阀':'Water supply valve','入侵感应':'Intrusion sensor','警戒合辙':'Alarm AND',
    '无人接线':'Empty-bay inverter','疏散旁路':'Evacuation bypass','警戒警报':'Security alarm',
    '请求合流':'Request OR','维护锁反相':'Service-lock inverter','辅助显影':'Auxiliary display',
    '试验压板':'Test plate','检修保险':'Service interlock','受控试验输出':'Controlled test output',
    '甲反相':'A inverter','乙反相':'B inverter','乙单路':'B-only AND','互斥合流':'Exclusive OR',
    '甲摆轮':'Clock A','乙摆轮':'Clock B','乙时相':'Clock B relay',
    '主线占用反相':'Primary-line inverter','备用供能':'Backup supply','维护断电':'Service disconnect',
    '主备合流':'Supply OR','应急供能':'Emergency supply','主备总线':'Supply bus',
    '备用显影':'Backup display','出口占用感应':'Exit occupancy sensor','出口空闲校验':'Clear-exit inverter',
    '复音寄存':'Repeated-note register','复位保险':'Reset interlock',
    '互斥钥码室':'Exclusive-key chamber','双摆校时院':'Twin-clock courtyard',
    '主备供能所':'Primary and backup supply station','应急显影站':'Emergency display station',
    '三段检修闸':'Three-stage service gate','复音保险库':'Repeated-note vault',
    '失物换乘站':'Lost-property interchange','记忆夜诊所':'Memory night clinic',
    '回声维修车间':'Echo repair workshop','梦种档案馆':'Dream-seed archive',
    '回返观测台':'Return observatory','未散场的排练厅':'Unfinished rehearsal hall',
    '留在原处，继续探索':'Leave it here and continue exploring',
    '换乘站的路线牌':'Interchange route board',
    '路线牌上三条线绕回同一个大厅，旁边留着一张没有盖章的票。':
        'Three routes loop back to the same hall. An unstamped ticket rests beside the board.',
    '取走候车票':'Take the waiting ticket','记下旁路，不拿车票':'Memorize the bypass; leave the ticket',
    '夜诊所的留观簿':'Night-clinic observation log',
    '值夜的人把急诊和休息床分在两边，叮嘱你别把一切疼痛都当作敌人。':
        'The night attendant separates emergency care from resting beds, reminding you that pain is not always an enemy.',
    '按簿上的办法休息片刻':'Rest as the log advises','取走床边的一罐咖啡':'Take the bedside coffee',
    '车间的维修工单':'Workshop service order',
    '工单把供能、校验和检修分成三栏，桌下留着一枚备用螺丝。':
        'The order separates power, verification and maintenance into three columns. A spare screw lies beneath the desk.',
    '收好备用螺丝':'Take the spare screw','读完检修顺序':'Read the service sequence',
    '档案馆的梦种账':'Archive dream-seed ledger',
    '编号不按年份而按回声排列；靠出口的一页仍然空白。':
        'Entries are ordered by echoes rather than years. The page nearest the exit is still blank.',
    '收下折好的书页':'Take the folded page','把空白页留给后来的人':'Leave the blank page for someone else',
    '观测台的回返图':'Observatory return chart',
    '图上画着入口、两条侧廊和回到入口的箭头。探索的终点不一定在最深处。':
        'The chart marks the entrance, two side passages and a return arrow. Exploration need not end at its deepest point.',
    '记住那条安全回路':'Memorize the safe return route','带走边缘的清醒玻璃':'Take the clear glass at the edge',
    '排练厅的未落幕声':'Rehearsal hall final echo',
    '一排空椅子面对侧台。你可以留下这一段，也可以把它带出去。':
        'Empty chairs face the side stage. You may leave this passage here, or carry it away.',
    '记住没有观众的和声':'Remember the harmony without an audience','收起未写完的乐谱':'Take the unfinished score',
    '检修出口的校验记录':'Service-exit verification log',
    '门后记录着每个输入与输出的关系：不是所有同时亮起的线都属于同一条电路。':
        'Behind the gate, a log records each input and output: traces that light together do not necessarily share a circuit.',
    '抄下检修记录':'Copy the service log','取走记录旁的螺丝':'Take the screw beside the log',
    '左、中的两个开关接入合辙，下面的维护开关必须断电。':
        'The upper and middle switches feed an AND gate. Keep the lower service switch off.',
    '先打开电源调相，让两只摆轮同相；门会记住一次同步。':
        'Turn on the power to align both clocks. The gate remembers one synchronized beat.',
    '依次踩一号、三号、二号压板，再打开校验使能。踩错可以从一号重新开始。':
        'Step on plates one, three, then two; turn on verification enable. After a mistake, restart at plate one.',
    '打开电源和通路校验，先清空灌注区的异象；水阀与门共用空区保险。':
        'Turn on power and path verification, then clear anomalies from the delivery bay. The valve and gate share its empty-bay interlock.',
    '无人时疏散门自动放行；有人时可打开维护旁路。打开电源才会启动警戒。':
        'The evacuation gate opens when the bay is empty. Use the service bypass when occupied. The alarm needs power.',
    '电源或通路校验任选一路，维护锁必须断电。辅助显影只显示维护状态。':
        'Use either power or path verification; keep the service lock off. The auxiliary display reports service status.',
    '先开维护旁路，储藏门打开且试验输出断电；试验压板不必踩。':
        'Enable the service bypass to open storage and disable the test output. You need not step on the test plate.',
    '先开维护旁路，储藏门打开且囚笼输出断电；试验压板不必踩。':
        'Enable the service bypass to open storage and disable the cage. You need not step on the test plate.',
    '只开电源或通路校验中的一个，两个都开会互相抵消；维护旁路保持断电。':
        'Enable exactly one of power and path verification. Both together cancel out. Keep the service bypass off.',
    '打开电源，乙摆轮与甲摆轮归于同相；等待同亮的一拍即可。':
        'Power aligns clock B with clock A. Wait for one beat when both are lit.',
    '主线电源优先，断开主线后备用供能才接管；维护开关必须断电。':
        'Primary power has priority; backup takes over when primary is off. Keep the service switch off.',
    '主线要电源和通路同时接通；应急供能可单独放行。两路显影各自报告。':
        'The main line requires both power and path verification. Emergency supply opens the gate alone. Each display reports its own line.',
    '打开电源和通路校验、保持维护断电，再清除出口附近的异象。':
        'Enable power and path verification, keep service off, then clear anomalies near the exit.',
    '依次踩低音、高音、低音压板。维护开关断电才开门；离开后仍可重新接通。':
        'Step on low, high, then low. The gate opens with service off; you can reconnect it after leaving.',
}
