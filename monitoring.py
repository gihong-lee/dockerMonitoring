import os
import time
from typing import Container

class monitoring:
  def __init__(self):
    self.containers = {}

    dockerIds = os.popen("docker ps -a | grep Up | awk '{print $1}'").read().split("\n")[:-1]

    for dockerId in dockerIds:
      ctName = os.popen("docker ps --format='{{.ID}} {{.Names}}'| grep %(id)s | awk '{print $2}'"%{"id":dockerId}).read().rstrip()
      veth = os.popen("cat ~/monitoring/vethInfo | grep %(id)s | awk '{print $3}'"%{"id":dockerId}).read().rstrip()

      self.containers[dockerId] = {"name":ctName, "veth": veth}

  def getPktInfo(self) -> dict:
    PktInfo = {}

    for dockerId in self.containers.keys():
      rtx = list(map(int, os.popen("""ifconfig %(veth)s | awk '{print $3 "\t" $5}'| sed -n -e '4p' -e '6p'"""%{"veth":self.containers[dockerId]["veth"]}).read().replace("\t","\n").split("\n")[:-1]))
      
      PktInfo[dockerId] = rtx

    return PktInfo

  def getMemUsage(self) -> dict:
    Usage = {}
    basePath = "/sys/fs/cgroup/memory/docker"

    for dockerId in self.containers.keys():
      fullId = os.popen(f"cd {basePath} && ls | grep {dockerId}").read().rstrip()
      perUsage = list(map(int,os.popen("cat %(basePath)s/%(fullId)s/memory.stat | sed -n -e '20p' -e '21p' | awk '{print $2}'"%{"basePath" : basePath, "fullId": fullId}).read().split("\n")[:-1]))
      
      Usage[dockerId] = perUsage[0] + perUsage[1]


    return Usage

  def getCpuUsage(self) -> dict:
    CpuUsage = {}
    basePath = "/sys/fs/cgroup/cpu,cpuacct/docker"

    for dockerId in self.containers.keys():
      fullId = os.popen(f"cd {basePath} && ls | grep {dockerId}").read().rstrip()
      perUsage = list(map(int, os.popen(f"cat {basePath}/{fullId}/cpuacct.usage_percpu").read().rstrip().split(" ")))

      CpuUsage[dockerId] = perUsage

    return CpuUsage

  def info(self) -> dict:
    ContainerInfo = {}

    bfPkt = self.getPktInfo()
    memUsage = self.getMemUsage()
    bfcpuUsage = self.getCpuUsage()
    time.sleep(1)
    afPkt = self.getPktInfo()
    afcpuUsage = self.getCpuUsage()

    for containerId in self.containers.keys():
      pktSub = []
      cpuSub = []

      for i in range(len(afPkt[containerId])):
        pktSub.append(afPkt[containerId][i] -  bfPkt[containerId][i])
      for i in range(len(afcpuUsage[containerId])):
        cpuSub.append(afcpuUsage[containerId][i]-bfcpuUsage[containerId][i])

      ContainerInfo[containerId] = {
        "name" : self.containers[containerId]['name'],
        "packet" : pktSub,
        "memory" : memUsage,
        "cpu" : cpuSub
      }
    
    return ContainerInfo

  def print(self):
    ContainerInfo = self.info()

    NLnum = 3

    for i in range(NLnum):
      print("")

    print (f"container ID\tName\t\t\t\t\tPacket\t\tMemory Usage\t\tCPU usage")

    for containerId in self.containers.keys():
      pkmsg = f"{ContainerInfo[containerId]['packet'][0]} --> {ContainerInfo[containerId]['packet'][2]}"
      containerName = ContainerInfo[containerId]['name']

      print(f'{containerId}\t{containerName}',end="")

      if(len(containerName) < 32):
        print("\t\t",end='')
      else:
        print("\t",end='')

      print(pkmsg,end="")

      if(len(pkmsg) < 8):
        print("\t\t",end='')
      else:
        print("\t",end='')

      print(f"{round(ContainerInfo[containerId]['memory'][containerId]/1000000,2)}\tMiB\t\t",end='')

      for core in ContainerInfo[containerId]['cpu']:
        print(core ,end='\t')

      print("")

    for i in range(54-NLnum-len(ContainerInfo.keys())):
      print("")

  def monitorStart(self):
    while(1):
      self.print()


if __name__ == "__main__":
  m = monitoring()
  m.monitorStart()
  # m.getMemUsage()
