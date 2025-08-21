
发电厂 = ['发电厂', '电厂', 'powr', '小电', '小电厂', '基础电厂', 'power plant', 'basic power plant', 'pp', 'pwr', 'power']
兵营 = ['兵营', '兵工厂', '苏军兵营', '红军兵营', 'soviet barracks', 'soviet inf', 'red barracks']
矿场 = ['矿场', 'proc', '矿', '精炼厂', '矿石精炼厂', 'ore refinery', 'ref', 'refinery', 'ore ref']
战车工厂 = ['weap', '战车工厂', '车间', '工厂', 'wf', 'factory', 'war factory']
雷达站 = ['dome', '雷达站', '雷达', '侦察站', '雷达圆顶', 'radar dome', 'radar station', 'rad', 'radar']
维修厂 = ['fix', '维修厂', '维修中心', '修理厂', '维修站', '修理站', 'service depot', 'repair factory', 'repair bay', 'rep', 'repair', 'serv']
核电站 = ['apwr', '核电', '核电站', '核电厂', '大电厂', '大电', '大电厂', '高级电厂', 'advanced power plant', 'nuclear reactor', 'nuke power', 'np', 'adv power']
科技中心 = ['stek', '科技中心', '高科技', '高科技中心', '研究中心', '实验室', 'tech center', 'research facility', 'tech', 'lab']
空军基地 = ['空军基地', 'afld', '空军基地', '机场', '飞机场', '航空站', 'airfield', 'airbase', 'air', 'af']
步兵 = ['步兵', 'e1', '枪兵', '步枪兵', '普通步兵', 'rifle infantry', 'basic infantry', 'rifle', 'rifleman']
火箭兵 = ['火箭兵', 'e3', '火箭筒兵', '炮兵', '火箭筒', '导弹兵', 'rocket soldier', 'rocket infantry', 'rocket', 'rl']
采矿车 = ['采矿车', 'harv', '采矿车', '矿车', '矿物收集车', 'ore collector', 'harvester', 'miner', 'harv', 'collector']
防空车 = ['防空车', 'ftrk', '防空炮车', '移动防控车', 'flak truck', 'mobile anti-air', 'flak', 'aa flak']
重型坦克 = ['重型坦克', '3tnk', '重坦', '犀牛坦克', '犀牛', 'heavy tank', 'rhino tank', 'ht', 'rhino']
V2火箭发射车 = ['V2火箭发射车', 'v2', 'V2', 'v2火箭发射车', '火箭炮', 'v2火箭', 'v2 rocket launcher', 'rl']
超重型坦克 = ['超重型坦克', '4tnk', '猛犸坦克', '猛犸', '天启坦克', '天启', 'mammoth tank', 'super heavy tank', 'mam', 'mammoth', 'mt']
防空炮 = ['防空炮', 'sam', '防空导弹', '防空塔', '防空炮塔', '山姆飞弹', 'sam site', 'surface-to-air missile', 'anti air']
特斯拉塔 = ['特斯拉塔', 'tsla', '电塔', '高级防御塔', 'tesla coil', 'tesla tower', 'tc', 'tes']


def unify_unit_name(name: str) -> str:
    '''
    统一单位名称，将名称转换为一个统一的名称
    Args:
        name (str): 单位名称
    Returns:
        str: 统一后的单位名称
    '''
    name = name.lower()
    if name in 发电厂:
        return '发电厂'
    elif name in 兵营:
        return '兵营'
    elif name in 矿场:
        return '矿场'
    elif name in 战车工厂:
        return '战车工厂'
    elif name in 雷达站:
        return '雷达站'
    elif name in 维修厂:
        return '维修厂'
    elif name in 核电站:
        return '核电站'
    elif name in 科技中心:
        return '科技中心'
    elif name in 空军基地:
        return '空军基地'
    elif name in 步兵:
        return '步兵'
    elif name in 火箭兵:
        return '火箭兵'
    elif name in 采矿车:
        return '采矿车'
    elif name in 防空车:
        return '防空车'
    elif name in 重型坦克:
        return '重型坦克'
    elif name in V2火箭发射车:
        return 'V2火箭发射车'
    elif name in 超重型坦克:
        return '超重型坦克'
    elif name in 防空炮:
        return '防空炮'
    elif name in 特斯拉塔:
        return '特斯拉塔'
    return name


def unify_queue_name(name: str) -> str:
    '''
    统一生产队列名称，将名称转换为一个统一的名称
    Args:
        name (str): 生产队列名称
    Returns:
        str: 统一后的生产队列名称
    '''
    name = name.lower()
    # todo
    return name