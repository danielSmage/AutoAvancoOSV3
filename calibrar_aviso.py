import pyautogui
import time

print('='*50)
print(' CALIBRADOR DE AVISO VERMELHO (RPA)')
print('='*50)
print('\nInstrucoes:')
print('1. Va no ERP e digite uma quantidade absurdamente alta para forcar o aviso vermelho.')
print('2. Quando o aviso vermelho aparecer na tela, DEIXE ELE LA.')
print('3. Coloque a ponta do SEU MOUSE exatamente em cima de alguma letra vermelha do aviso.')
print('4. Aguarde 5 segundos sem mexer o mouse...\n')

for i in range(5, 0, -1):
    print(f'Lendo em {i}...')
    time.sleep(1)

x, y = pyautogui.position()
cor = pyautogui.pixel(x, y)

print('\n' + '='*50)
print(' CALIBRACAO CONCLUIDA!')
print(f' Coordenada X: {x}')
print(f' Coordenada Y: {y}')
print(f' Cor RGB do Pixel: {cor}')
print('='*50)
print('\nAbra o arquivo modulos/rpa_bot.py e coloque esses valores nas variaveis AVISO_X e AVISO_Y na linha ~110.')
input('\nPressione Enter para sair...')
