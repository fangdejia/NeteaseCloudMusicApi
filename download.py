import subprocess
import requests
from pyms import play
limit=30
download_path="./download/"
while 1:
    cmd=input("请输入需要执行的指令:搜索(s)/下一页(n)/下载并试听(d):").strip()
    if cmd=='s':
        keyword=input("请输入歌曲名:")
        offset=0
    if cmd in ['s','n','p']:
        data=requests.get(f"http://localhost:3000/search?keywords={keyword}&offset={offset}&limit={limit}").json()
        songs=data['result']['songs']
        good_songs=[]
        count=1
        for d in songs:
            if d['fee'] in [0,8]:
                artist='|'.join([e['name'] for e in d['artists']][:3]).replace("/","|")
                good_songs.append((d['id'],d['name'].replace("/","|"),artist))
                print(count,"|",d['name'],"|",artist,"|时长:",round(d['duration']/1000/60,1),"分钟","|",d['id'])
                count+=1
        if cmd in ['s','n']:
            offset+=len(songs)
        else:
            offset-=len(songs)
    elif (cmd=='d' or cmd.isdigit()) and good_songs:
        if cmd.isdigit():
            idx=int(cmd)-1
        else:
            idx=int(input("输入需要下载的歌曲序号:"))-1
        mid,name,artist=good_songs[idx]
        data=requests.get(f"http://localhost:3000/song/url?id={mid}").json()
        mp3_url=data['data'][0]['url']
        #todo 下载mp3
        if mp3_url:
            response = requests.get(mp3_url,timeout=10)
            file_name=f"{name}-{artist}.mp3"
            file_path=download_path+file_name
            with open(file_path, 'wb') as file:
                file.write(response.content)
            print(f"歌曲已下载: {file_name}")
            subprocess.run(["tput", "smcup"], check=True)
            play(file_path)
            subprocess.run(["tput", "rmcup"], check=True)
            #播放
        else:
            print("无法下载歌曲，URL无效。")

