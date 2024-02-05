node app.js &
python download.py

on_sigint() {
     echo "接收到 SIGINT 信号，正在终止所有程序..."
     for prog_feature in "node app.js" "python download.py"; do
         pids=$(pgrep -f "$prog_feature")
         if [ -n "$pids" ]; then
             kill -9 $pids
         else
             echo "没有找到与 $prog_feature 匹配的进程。"
         fi
     done
     exit
 }
 trap 'on_sigint' SIGINT
