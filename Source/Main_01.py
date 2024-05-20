# Ref: https://graphics.stanford.edu/~mdfisher/cloth.html

import taichi as ti
# taichi version: 0.8.1
#Main 01: Wind
resfolder = '../results/main01wind/'
ti.init(arch=ti.cuda)

Mu = 0.2

# Air resistance
A = 0.01

massLengthA = 0.1
massLengthB = ti.sqrt(2 * massLengthA * massLengthA)
massK      = 20000.0

pointMass = 0.2

widthSize,heightSize = 127, 127

faceSize = widthSize * heightSize * 2

pointSize = (widthSize + 1) * (heightSize + 1)

pointLocation = ti.Vector.field(3, dtype=ti.f32, shape=pointSize)
pointVelocity = ti.Vector.field(3, dtype=ti.f32, shape=pointSize)
pointForce    = ti.Vector.field(3, dtype=ti.f32, shape=pointSize)

Idx = ti.field(dtype=ti.i32, shape=faceSize * 3)

# Y Forward
G = ti.Vector([0.0, 0.0, -9.8], dt=ti.f32)

Wind = ti.Vector([1.0, 1.0, 0.0], dt=ti.f32)

@ti.func
def pointID(x,y):
  R = -1
  if 0 <= x and x <= widthSize and 0 <= y and y <= heightSize:
    R = y * (widthSize + 1) + x
  return R

def pointIDPy(x,y):
  R = -1
  if 0 <= x and x <= widthSize and 0 <= y and y <= heightSize:
    R = y * (widthSize + 1) + x
  return R

@ti.func
def pointCoord(ID):
  return (ID % (widthSize + 1), ID // (widthSize + 1))

@ti.func
def massID(ID):
  R = ti.Vector([-1, -1, -1, -1, -1, -1, -1, -1], dt=ti.i32)
  x,y = pointCoord(ID)
  R[0],R[1] = pointID(x-1, y),pointID(x+1, y)
  R[2],R[3] = pointID(x, y-1),pointID(x, y+1)
  R[4],R[5] = pointID(x-1,y-1),pointID(x+1,y+1)
  R[6],R[7] = pointID(x-1,y+1),pointID(x+1,y-1)
  return R

@ti.kernel
def InitTi():
  for i in range(pointSize):
    x,y = pointCoord(i)
    pointLocation[i] = (x * massLengthA, y * massLengthA, 6)
    pointVelocity[i] = (0, 0, 0)

@ti.kernel
def ComputeForce():
  for i in pointForce:
    pointForce[i] = (0, 0, 0)
    Dirs = massID(i)
    for j in ti.static(range(0,4)):
      if not Dirs[j] == -1:
        Dir = pointLocation[Dirs[j]] - pointLocation[i]
        pointForce[i] += (Dir.norm() - massLengthA) * massK * Dir / Dir.norm()
    for j in ti.static(range(4,8)):
      if not Dirs[j] == -1:
        Dir = pointLocation[Dirs[j]] - pointLocation[i]
        pointForce[i] += (Dir.norm() - massLengthB) * massK * Dir / Dir.norm()
    pointForce[i] += G * pointMass + Wind
    pointForce[i] += A * pointVelocity[i] * pointVelocity[i]

  pointForce[pointID(0,0)] = (0, 0, 0)
  pointForce[pointID(0,heightSize)] = (0, 0, 0)

@ti.kernel
def Forward(T: ti.f32):
  for i in range(pointSize):
    pointVelocity[i] += T * pointForce[i] / pointMass
    pointLocation[i] += T * pointVelocity[i]

@ti.kernel
def ComputeCollsion():
  pass

def Init():
  InitTi()

  Index = 0
  for i in range(widthSize):
    for j in range(heightSize):
      ID_1 = pointIDPy(i,j)
      ID_2 = pointIDPy(i+1,j)
      ID_3 = pointIDPy(i,j+1)
      ID_4 = pointIDPy(i+1,j+1)

      Idx[Index + 0] = ID_1
      Idx[Index + 1] = ID_2
      Idx[Index + 2] = ID_3
      Idx[Index + 3] = ID_2
      Idx[Index + 4] = ID_3
      Idx[Index + 5] = ID_4

      Index += 6

def Step():
  for i in range(50):
    ComputeForce()
    Forward(0.00001)

def Export(i: int):
  npL = pointLocation.to_numpy()
  npI = Idx.to_numpy()

  mesh_writer = ti.PLYWriter(num_vertices=pointSize, num_faces=faceSize, face_type="tri")
  mesh_writer.add_vertex_pos(npL[:, 0], npL[:, 1], npL[:, 2])
  mesh_writer.add_faces(npI)

  mesh_writer.export_frame_ascii(i, resfolder+'S.ply')

  print('Frame >> %03d'%(i))

def main():
  Init()
  Frame = 0
  try:
    while True:
      Step()

      Frame += 1
      if not Frame % 50:
        Export(Frame // 50)
  except Exception as Error:
    print(Error)

if __name__=='__main__':
  main()