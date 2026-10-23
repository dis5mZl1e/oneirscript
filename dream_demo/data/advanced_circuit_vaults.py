"""Large, distinct PCB rooms; topology and traversal are authored together."""
from .circuit_templates import component, connect_board

KINDS = ('interlock', 'phase_lock', 'sequence_lock', 'safe_pump', 'sensor_bypass', 'crossbar',
         'trap_interlock', 'cage_interlock', 'xor_gate', 'dual_clock', 'service_priority',
         'emergency_bus', 'three_stage', 'resettable_code')


def advanced_board(kind):
    if kind not in KINDS:
        raise ValueError(f'Unknown advanced board: {kind}')
    w, h = 25, 19
    # An entry spine links three input bays. The reward wing is controlled by
    # a single latched door, never by a route that opens to the outside world.
    rows = [['#' if x in (0,w-1) or y in (0,h-1) or x == 19 else '.'
             for x in range(w)] for y in range(h)]
    for y in (6,12):
        for x in range(1,19):
            if x not in (2,9,16):
                rows[y][x] = '#'
    for y in range(1,18):
        if y not in (3,9,15):rows[y][7] = '#'
    rows[18][2] = '@'
    rows[3][22] = 'S'
    rows[15][22] = 'S'
    n = {
        'a': component(4,3,'toggle','电源开关','机关石台'),
        'b': component(4,9,'toggle','通路校验','机关石台'),
        'c': component(4,15,'toggle','维护旁路','机关石台'),
        'ab': component(11,3,'and','双源合辙','合辙枢',('a','b')),
        'nc': component(11,15,'not','旁路反相','接线枢',('c',)),
        'ready': component(16,9,'and','终段校验','合辙枢',('ab','nc')),
        'door': component(19,9,'output','储藏门','机关门',('ready',),latch=True),
        'lamp': component(16,3,'output','状态显影','显影方尖',('ab',)),
    }
    if kind == 'phase_lock':
        n['b'] = component(4,9,'timer','基准摆轮','定时摆轮',period=12,window=4)
        n['c'] = component(11,15,'timer','调相摆轮','定时摆轮',('a',),period=12,window=4,
                           phase=6,phase_input='a',on_phase=0)
        n['nc'] = component(14,15,'or','相位接线','分流枢',('c',))
        n['ab']['inputs']=['a','b']
    elif kind == 'sequence_lock':
        n['a'] = component(4,3,'step','一号压板')
        n['b'] = component(4,9,'step','二号压板')
        n['c'] = component(4,15,'step','三号压板')
        n['ab'] = component(11,3,'sequence','音序寄存','接线枢',('a','b','c'),order=['a','c','b'])
        n['nc'] = component(11,15,'toggle','校验使能','机关石台')
    elif kind == 'safe_pump':
        n['c'] = component(4,15,'sensor','灌注区感应','感应符文墙',radius=3)
        n['pump'] = component(16,15,'output','供水阀','灌注阀',('ready',))
        # Powered, verified and empty delivery bay. Occupancy blocks the pump.
        n['nc']['inputs']=['c']
    elif kind == 'sensor_bypass':
        n['b'] = component(4,9,'sensor','入侵感应','感应符文墙',radius=3)
        n['ab'] = component(11,3,'and','警戒合辙','合辙枢',('a','b'))
        n['nc'] = component(11,15,'not','无人接线','接线枢',('b',))
        n['ready'] = component(16,9,'or','疏散旁路','分流枢',('c','nc'))
        n['lamp'].update(wall='共鸣报警器',label='警戒警报')
    elif kind == 'crossbar':
        n['ab'] = component(11,3,'or','请求合流','分流枢',('a','b'))
        n['nc'] = component(11,15,'not','维护锁反相','接线枢',('c',))
        n['aux'] = component(16,15,'output','辅助显影','显影方尖',('nc',))
    elif kind in ('trap_interlock', 'cage_interlock'):
        n['b'] = component(4,9,'plate','试验压板')
        n['nc'] = component(11,15,'not','检修保险','接线枢',('c',))
        n['hazard'] = component(16,15,'output','受控试验输出',
                                 '陷阱石台' if kind == 'trap_interlock' else '囚笼栅栏',('ready',))
        n['door']['inputs']=['c']  # maintenance opens the exit and disables hazard
    elif kind == 'xor_gate':
        n['na'] = component(9,9,'not','甲反相','接线枢',('a',))
        n['nb'] = component(11,15,'not','乙反相','接线枢',('b',))
        n['ab']['inputs']=['a','nb']
        n['nc'] = component(14,15,'and','乙单路','合辙枢',('b','na'))
        n['merge'] = component(14,9,'or','互斥合流','分流枢',('ab','nc'))
        n['service'] = component(13,15,'not','检修保险','接线枢',('c',))
        n['ready']['inputs'] = ['merge','service']
    elif kind == 'dual_clock':
        n['b'] = component(4,9,'timer','甲摆轮','定时摆轮',period=10,window=4)
        n['c'] = component(4,15,'timer','乙摆轮','定时摆轮',('a',),period=10,window=4,
                           phase=5,phase_input='a',on_phase=0)
        n['ab']['inputs']=['a','b']
        n['nc'] = component(11,15,'or','乙时相','分流枢',('c',))
    elif kind == 'service_priority':
        n['nb'] = component(9,9,'not','主线占用反相','接线枢',('a',))
        n['ab'] = component(11,3,'and','备用供能','合辙枢',('b','nb'))
        n['nc'] = component(11,15,'not','维护断电','接线枢',('c',))
        n['merge'] = component(14,9,'or','主备合流','分流枢',('a','ab'))
        n['ready']['inputs']=['merge','nc']
    elif kind == 'emergency_bus':
        n['ab']['inputs']=['a','b']
        n['nc'] = component(11,15,'or','应急供能','分流枢',('c',))
        n['ready'] = component(16,9,'or','主备总线','分流枢',('ab','nc'))
        n['aux'] = component(16,15,'output','备用显影','显影方尖',('nc',))
        n['lamp']['inputs']=['ab']
    elif kind == 'three_stage':
        n['sensor'] = component(13,9,'sensor','出口占用感应','感应符文墙',radius=2)
        n['free'] = component(16,15,'not','出口空闲校验','接线枢',('sensor',))
        n['ready']['inputs']=['ab','nc','free']
    elif kind == 'resettable_code':
        n['a'] = component(4,3,'step','低音压板')
        n['b'] = component(4,9,'step','高音压板')
        n['ab'] = component(11,3,'sequence','复音寄存','接线枢',('a','b'),order=['a','b','a'])
        n['nc'] = component(11,15,'not','复位保险','接线枢',('c',))
        n['door']['latch']=False  # maintenance disconnects access without trapping entry
    chars={'机关石台':'M','合辙枢':'U','接线枢':'Y','分流枢':'I','机关门':'D',
           '显影方尖':'B','定时摆轮':'O','灌注阀':'V','感应符文墙':'R','共鸣报警器':'L',
           '陷阱石台':'X','囚笼栅栏':'K'}
    for node in n.values():
        x,y=node['pos'];rows[y][x]=chars[node['wall']] if node['wall'] else 'p'
    hints = {
        'interlock': '左、中的两个开关接入合辙，下面的维护开关必须断电。',
        'phase_lock': '先打开电源调相，让两只摆轮同相；门会记住一次同步。',
        'sequence_lock': '依次踩一号、三号、二号压板，再打开校验使能。踩错可以从一号重新开始。',
        'safe_pump': '打开电源和通路校验，先清空灌注区的异象；水阀与门共用空区保险。',
        'sensor_bypass': '无人时疏散门自动放行；有人时可打开维护旁路。打开电源才会启动警戒。',
        'crossbar': '电源或通路校验任选一路，维护锁必须断电。辅助显影只显示维护状态。',
        'trap_interlock': '先开维护旁路，储藏门打开且试验输出断电；试验压板不必踩。',
        'cage_interlock': '先开维护旁路，储藏门打开且囚笼输出断电；试验压板不必踩。',
        'xor_gate': '只开电源或通路校验中的一个，两个都开会互相抵消；维护旁路保持断电。',
        'dual_clock': '打开电源，乙摆轮与甲摆轮归于同相；等待同亮的一拍即可。',
        'service_priority': '主线电源优先，断开主线后备用供能才接管；维护开关必须断电。',
        'emergency_bus': '主线要电源和通路同时接通；应急供能可单独放行。两路显影各自报告。',
        'three_stage': '打开电源和通路校验、保持维护断电，再清除出口附近的异象。',
        'resettable_code': '依次踩低音、高音、低音压板。维护开关断电才开门；离开后仍可重新接通。',
    }
    board=connect_board({'id':kind,'nodes':n,'completion':'door','hint':hints[kind],
                         'source_template':f'pcb_{kind}'},w,h)
    # The traces are owned nets (insulated crossings); their visible map overlay
    # comes from install_circuit_board, not a string of alphabetic component IDs.
    return [''.join(r) for r in rows],board
