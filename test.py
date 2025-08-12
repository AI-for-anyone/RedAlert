from OpenRA_Copilot_Library.game_api import GameAPI
from OpenRA_Copilot_Library.models import Location, TargetsQueryParam, Actor,MapQueryResult

api = GameAPI('127.0.0.1', 7445)

print(api.player_base_info_query())
print(api.deploy_mcv_and_wait())
print(api.query_actor(TargetsQueryParam(type=[], faction=["任意"], range="screen", restrain=[{"visible": True}])))
api.move_camera_by_location(Location(30, 25))
# 部署基地车
if api.can_produce('电厂'):
    print("建造两个电厂")
    api.wait(api.produce('电厂', 2, True))
else:
    print('电厂无法生产')

if api.can_produce('proc'):
    print("建造一个proc")
    api.wait(api.produce('proc', 1, True))
else:
    print('proc无法生产')

if api.can_produce('兵营'):
    print("建造一个兵营")
    api.wait(api.produce('兵营',1,True))
else:
    print('兵营无法生产')

if api.can_produce('步兵'):
    print("建造三个步兵")
    api.produce('步兵',3,True)
else:
    print('步兵无法生产')

if api.can_produce('战车工厂'):
    print("建造一个战车工厂")
    api.wait(api.produce('战车工厂',1,True))
else:
    print('战车工厂无法生产')

if api.can_produce('防空车'):
    print("建造两个防空车")
    api.produce('防空车',2,True)
else:
    print('防空车无法生产')

if api.can_produce('雷达'):
    print("建造一个雷达")
    api.wait(api.produce('雷达',1,True))
else:
    print('雷达无法生产')

if api.can_produce('核电厂'):
    print("建造一个核电厂")
    api.wait(api.produce('核电厂',1,True))
else:
    print('核电厂无法生产')