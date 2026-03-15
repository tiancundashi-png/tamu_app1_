#ランダムで数字を決める
import random
answer = random.randint(1,10)
number = int(input('1~10の数字を入力してください'))
if answer == number:
    print('正解です！')
elif answer > number:
    print('もっと大きいです')
else:
    print('もっと小さいです')
    