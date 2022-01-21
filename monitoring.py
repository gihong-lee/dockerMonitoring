import os
import time
from typing import Container
import datetime


class monitoring:
  def __init__(self):
    self.containers = {}

    dockerIds = os.popen("docker ps -a | grep Up | awk '{print $1}'").read().split("\n")[:-1]

    for dockerId in dockerIds:
      ctName = os.popen("docker ps --format='{{.ID}} {{.Names}}'| grep %(id)s | awk '{print $2}'"%{"id":dockerId}).read().rstrip()
      task = os.popen(f'cat /sys/fs/cgroup/devices/docker/{dockerId}*/tasks').read().split()[0]
      os.system('mkdir -p /var/run/netns')
      os.system(f'ln -sf /proc/{task}/ns/net /var/run/netns/{dockerId}')

      self.containers[dockerId] = {"name":ctName, "task": task}

  def getPktInfo(self) -> dict:
    PktInfo = {}

    for dockerId,items in self.containers.items():
      rtx = [0, 0]
      data = list(map(int,os.popen("""ip netns exec %(dockerId)s netstat -in | grep -P "eth|lo" | awk '{print $3 "\t" $7}'"""%{"dockerId":dockerId}).read().split()))

      for i in range(len(data)):
        if i%2 == 0:
          rtx[0] += data[i]
        else:
          rtx[1] += data[i]
      
      PktInfo[dockerId] = rtx

    return PktInfo

  def getMemUsage(self) -> dict:
    Usage = {}
    basePath = "/sys/fs/cgroup/memory/docker"

    for dockerId in self.containers:
      perUsage = list(map(int,os.popen("cat %(basePath)s/%(dockerId)s*/memory.stat | sed -n -e '20p' -e '21p' | awk '{print $2}'"%{"basePath" : basePath, "dockerId": dockerId}).read().split("\n")[:-1]))
      
      Usage[dockerId] = perUsage[0] + perUsage[1]


    return Usage

  def getCpuUsage(self) -> dict:
    CpuUsage = {}
    basePath = "/sys/fs/cgroup/cpu,cpuacct/docker"

    for dockerId in self.containers:
      perUsage = list(map(int, os.popen(f"cat {basePath}/{dockerId}*/cpuacct.usage_percpu").read().rstrip().split(" ")))

      CpuUsage[dockerId] = perUsage

    return CpuUsage

  def getInfo(self) -> dict:
    ContainerInfo = {}

    bfPkt = self.getPktInfo()
    memUsage = self.getMemUsage()
    bfcpuUsage = self.getCpuUsage()
    time.sleep(1)
    afPkt = self.getPktInfo()
    afcpuUsage = self.getCpuUsage()

    for containerId, items in self.containers.items():
      pktSub = []
      cpuSub = []

      for i in range(len(afPkt[containerId])):
        pktSub.append(afPkt[containerId][i] -  bfPkt[containerId][i])
      for i in range(len(afcpuUsage[containerId])):
        cpuSub.append(afcpuUsage[containerId][i]-bfcpuUsage[containerId][i])
      
      ContainerInfo[containerId] = {
        "name" : items['name'],
        "packet" : pktSub,
        "memory" : memUsage[containerId],
        "cpu" : cpuSub
      }
    
    return ContainerInfo

  def getMSG(self) -> str:
    ContainerInfo = self.getInfo()

    NLnum = 3
    msg = ''

    for i in range(NLnum):
      msg = msg + "\n"

    for containerId in self.containers:
      pkmsg = f"{ContainerInfo[containerId]['packet'][0]} --> {ContainerInfo[containerId]['packet'][1]}"
      containerName = ContainerInfo[containerId]['name'][:35]

      msg = msg + f'{containerId}\t{containerName}'

      if(len(containerName) < 32):
        msg = msg + "\t\t"
      else:
        msg = msg + "\t"

      msg = msg + pkmsg

      if(len(pkmsg) < 8):
        msg = msg + "\t\t"
      else:
        msg = msg + "\t"

      msg = msg + f"{round(ContainerInfo[containerId]['memory']/1000000,2)}\tMiB\t\t"

      for core in ContainerInfo[containerId]['cpu']:
        msg = msg + str(core) +'\t'
      msg = msg + '\n'

    for i in range(54-NLnum-len(ContainerInfo.keys())):
      msg = msg + '\n'
    
    return msg 

  def monitorPrint(self):
    d = datetime.datetime.now()

    while(1):
      msg = self.getMSG()
      # print("container ID\tName\t\t\t\t\tPacket\t\tMemory Usage\t\tCPU usage")
      # print(msg)
      f = open(f"/home/gh/exp_result/exp_redis/monitor_{d.year}_{d.month}_{d.day}",'a')
      f.write(msg.rstrip('\n'))
      f.close()



if __name__ == "__main__":
  m = monitoring()
  m.monitorPrint()

