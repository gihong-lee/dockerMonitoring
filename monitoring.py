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

  def getInfo(self) -> dict:
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

    msg = msg + f"container ID\tName\t\t\t\t\tPacket\t\tMemory Usage\t\tCPU usage\n"

    for containerId in self.containers.keys():
      pkmsg = f"{ContainerInfo[containerId]['packet'][0]} --> {ContainerInfo[containerId]['packet'][2]}"
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
    while(1):
      msg = self.getMSG()
      print(msg)




if __name__ == "__main__":
  m = monitoring()
  m.monitorPrint()

