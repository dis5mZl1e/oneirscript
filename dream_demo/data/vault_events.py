"""Single-use, authored scene interactions. No extra random event quota."""

SCENES = (
    ('route_board','换乘站的路线牌','路线牌上三条线绕回同一个大厅，旁边留着一张没有盖章的票。',
     [('取走候车票','quiet_ticket',{}),('记下旁路，不拿车票',None,{'imagination':2})]),
    ('quiet_ward','夜诊所的留观簿','值夜的人把急诊和休息床分在两边，叮嘱你别把一切疼痛都当作敌人。',
     [('按簿上的办法休息片刻',None,{'mind':2}),('取走床边的一罐咖啡','warm_coffee',{})]),
    ('repair_desk','车间的维修工单','工单把供能、校验和检修分成三栏，桌下留着一枚备用螺丝。',
     [('收好备用螺丝','model_screw',{}),('读完检修顺序',None,{'imagination':2})]),
    ('seed_ledger','档案馆的梦种账','编号不按年份而按回声排列；靠出口的一页仍然空白。',
     [('收下折好的书页','folded_projectile',{}),('把空白页留给后来的人',None,{'lucidity':2})]),
    ('return_loop','观测台的回返图','图上画着入口、两条侧廊和回到入口的箭头。探索的终点不一定在最深处。',
     [('记住那条安全回路',None,{'lucidity':2}),('带走边缘的清醒玻璃','clear_glass',{})]),
    ('rehearsal','排练厅的未落幕声','一排空椅子面对侧台。你可以留下这一段，也可以把它带出去。',
     [('记住没有观众的和声',None,{'mind':2}),('收起未写完的乐谱','unfinished_song_memory',{})]),
    ('circuit_log','检修出口的校验记录','门后记录着每个输入与输出的关系：不是所有同时亮起的线都属于同一条电路。',
     [('抄下检修记录',None,{'imagination':2}),('取走记录旁的螺丝','model_screw',{})]),
)

VAULT_EVENT_DEFINITIONS = tuple(dict(
    event_id='event.vault_'+key, name=name, description=desc,
    catalog_id='event.vault_'+key, kind='compound', dialogue=[desc],
    uses=1, dissolution_reward=0,
    options=[dict(label=label, **({'reward_id':item} if item else {}), **effect)
             for label,item,effect in options] + [{'label':'留在原处，继续探索','leave':True}],
) for key,name,desc,options in SCENES)
