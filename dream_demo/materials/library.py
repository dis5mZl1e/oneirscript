"""Finite palace scenery built on ordinary material physics."""
from .definitions import WallDef

WALLS={
 '藏书宫外墙':WallDef('藏书宫外墙','wall.library.outer','#4b382b',999,4,4,9999,spawn_realms=('library_palace',)),
 '书库内墙':WallDef('书库内墙','wall.library.inner','#876c4a',4,3,2,180,spawn_realms=('library_palace',)),
 '玻璃书障':WallDef('玻璃书障','wall.library.glass','#a8c4b8',1,3,1,55,transparent=True,spawn_realms=('library_palace',)),
 '胡桃木书架':WallDef('胡桃木书架','wall.library.shelf','#72563b',2,3,1,55,flammable=True,spawn_realms=('library_palace',)),
 '推书车':WallDef('推书车','wall.library.cart','#947044',2,2,1,60,pushable=True,flammable=True,spawn_realms=('library_palace',)),
 '防火书柱':WallDef('防火书柱','wall.library.pillar','#a3987c',4,3,2,180,spawn_realms=('library_palace',)),
 '黄铜阅读灯':WallDef('黄铜阅读灯','wall.library.lamp','#b08b45',2,1,1,50,light_radius=3,spawn_realms=('library_palace',)),
}


