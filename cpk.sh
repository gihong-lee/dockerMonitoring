#!/bin/bash

VETHS=`ifconfig -a | grep flags | sed 's/ .*//g' | sed 's/.$//'`
DOCKERS=$(docker ps -a | grep Up | awk '{print $1}')

for VETH in $VETHS
do
  IFINDEX=`cat /sys/class/net/$VETH/ifindex`

  for DOCKER in $DOCKERS
  do
    # PEER_IF=`docker exec $DOCKER ip link list 2>/dev/null | grep "^$PEER_IFINDEX:" | awk '{print $2}' | sed 's/:.*//g'`
    IF=`docker exec $DOCKER /bin/cat /sys/class/net/eth1/iflink`
    
    if [ $IF = $IFINDEX ]; then
      echo "$DOCKER : $VETH" >> ~/monitoring/vethInfo
      break
    else
      continue
    fi
  done
done
