#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import aiohttp
import requests
import random
import json
import re
import sys

from . import config
from bs4 import BeautifulSoup
from struct import *


class bilibili():
    def __init__(self, roomId, server):
        self._roomId = roomId
        self._ChatPort = 788
        self._protocolversion = 1
        self._reader = 0
        self._writer = 0
        self.connected = False
        self._UserCount = 0
        self._ChatServer = server

    async def connectServer(self):
        print ('正在进入房间...')
        reader, writer = await asyncio.open_connection(self._ChatServer, self._ChatPort)
        self._reader = reader
        self._writer = writer
        print ('链接弹幕中...')
        if (await self.SendJoinChannel(self._roomId) == True):
            self.connected = True
            print ('进入房间成功...')
            print ('链接弹幕成功...')
            await self.ReceiveMessageLoop()

    async def HeartbeatLoop(self):
        while self.connected == False:
            await asyncio.sleep(0.5)

        while self.connected == True:
            await self.SendSocketData(0, 16, self._protocolversion, 2, 1, "")
            await asyncio.sleep(30)


    async def SendJoinChannel(self, channelId):
        self._uid = (int)(100000000000000.0 + 200000000000000.0*random.random())
        body = '{"roomid":%s,"uid":%s}' % (channelId, self._uid)
        await self.SendSocketData(0, 16, self._protocolversion, 7, 1, body)
        return True

    async def SendSocketData(self, packetlength, magic, ver, action, param, body):
        bytearr = body.encode('utf-8')
        if packetlength == 0:
            packetlength = len(bytearr) + 16
        sendbytes = pack('!IHHII', packetlength, magic, ver, action, param)
        if len(bytearr) != 0:
            sendbytes = sendbytes + bytearr
        self._writer.write(sendbytes)
        await self._writer.drain()


    async def ReceiveMessageLoop(self):
        while self.connected == True:
            tmp = await self._reader.read(4)
            expr, = unpack('!I', tmp)
            tmp = await self._reader.read(2)
            tmp = await self._reader.read(2)
            tmp = await self._reader.read(4)
            num, = unpack('!I', tmp)
            tmp = await self._reader.read(4)
            num2 = expr - 16

            if num2 != 0:
                num -= 1
                if num==0 or num==1 or num==2:
                    tmp = await self._reader.read(4)
                    num3, = unpack('!I', tmp)
                    print ('房间人数为 %s' % num3)
                    self._UserCount = num3
                    continue
                elif num==3 or num==4:
                    tmp = await self._reader.read(num2)
                    try:
                        messages = tmp.decode('utf-8')
                    except:
                        continue
                    self.parseDanMu(messages)
                    continue
                elif num==5 or num==6 or num==7:
                    tmp = await self._reader.read(num2)
                    continue
                else:
                    if num != 16:
                        tmp = await self._reader.read(num2)
                    else:
                        continue

    def parseDanMu(self, messages):
        try:
            dic = json.loads(messages)
        except:
            return
        cmd = dic['cmd']
        if cmd == 'LIVE':
            print ('直播开始...')
            return
        if cmd == 'PREPARING':
            print ('房主准备中...')
            return
        if cmd == 'DANMU_MSG':
            commentText = dic['info'][1]
            commentUser = dic['info'][2][1]
            isAdmin = dic['info'][2][2] == '1'
            isVIP = dic['info'][2][3] == '1'
            if isAdmin:
                commentUser = '管理员 ' + commentUser
            if isVIP:
                commentUser = 'VIP ' + commentUser
            try:
                print (commentUser + ' : ' + commentText)
            except:
                pass
            return
        if cmd == 'SEND_GIFT' and config.TURN_GIFT == 1:
            GiftName = dic['data']['giftName']
            GiftUser = dic['data']['uname']
            Giftrcost = dic['data']['rcost']
            GiftNum = dic['data']['num']
            try:
                print(GiftUser + ' 送出了 ' + str(GiftNum) + ' 个 ' + GiftName)
            except:
                pass
            return
        if cmd == 'WELCOME' and config.TURN_WELCOME == 1:
            commentUser = dic['data']['uname']
            try:
                print ('欢迎 ' + commentUser + ' 进入房间....')
            except:
                pass
            return
        return

def main():
    argv = sys.argv[1:]
    try:
        if len(argv) > 1:
            raise ValueError
        elif int(argv[0]):
            roomId = int(argv[0])
            getInfo(roomId)
    except ValueError:
        print('请输入正确的房间号!')
    except:
        print('请输入正确的房间号!')

"""
获取真正的房间ID和Server
此处有bug, 部分老主播的ID不是ROOMURL和ROOMID不同
"""
def getInfo(roomId):
    res = requests.get('http://live.bilibili.com/api/player?id=cid:{0}'.format(roomId))

    if res.status_code == 200:
        soup = BeautifulSoup(res.text,'lxml')
        roomId = soup.find('chatid').get_text()
        server = soup.find('server').get_text()
        start(roomId, server)
    else:
        raise ValueError

def start(roomId, server):
    danmuji = bilibili(roomId, server)
    tasks = [
                danmuji.connectServer() ,
                danmuji.HeartbeatLoop()
            ]
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(asyncio.wait(tasks))
    except KeyboardInterrupt:
        danmuji.connected = False
        for task in asyncio.Task.all_tasks():
            task.cancel()
        loop.run_forever()

    loop.close()

if __name__ == '__main__':
    main()
