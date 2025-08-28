from OpenRA_Copilot_Library import AsyncGameAPI
from OpenRA_Copilot_Library.models import Location, NewTargetsQueryParam, Actor
from typing import List
import asyncio

fight_api = AsyncGameAPI(host="localhost", port=7445, language="zh")

async def main():
    actors = await fight_api.query_actor(NewTargetsQueryParam(type=["雅克战机"]))
    locs:List[Location] = [
        Location(19, 28),
        Location(16, 32),
        Location(11, 34),
        Location(8, 35),
        Location(5, 32),

        Location(8, 5),
        Location(5, 8),

        Location(32, 5),
        Location(36, 8),

        Location(35, 35)
    ]
    await fight_api.move_units_by_path(actors=[Actor(actor_id=ac.actor_id) for ac in actors], path=locs)

if __name__ == "__main__":
    asyncio.run(main())