# Bot de Telegram: LambdaCalculBot

## Descripció
Aquest projecte és un bot de Telegram que avalua expressions en lambda càlcul que l'usuari envia mitjançant l'aplicació Telegram.

## Funcionalitats principals

- Avaluació d'expressions de càlcul lambda: Realitza alpha conversions i beta reduccions fins a obtenir l'expressió en forma normal.
- Definició de macros: Permet als usuaris definir les seves pròpies macros.
- Representació gràfica de les expressions: Mostra visualment les expressions com un arbre semàntic.
- Configuracions personalitzades: Permet als usuaris definir les seves pròpies configuracions, com ara establir el nombre màxim de beta reduccions permeses per avaluació.

## Tecnologies utilitzades

- antlr4 per definir la gramàtica.
- Python i la llibreria python-telegram-bot per a la implementació del bot.
- pydot i GraphViz per a la representació gràfica de les expressions.

## Dependències

Assegura't de tenir les següents dependències instal·lades abans de començar:

- python3.10: Versió de Python necessària per executar el bot.
- antlr4: Llibreria d'anàlisi gramatical per a la manipulació de llenguatges formals.
- python-telegram-bot: Llibreria per interactuar amb l'API de Telegram des de Python.
- pip: Gestor de paquets de Python. Verifica que tinguis una versió actualitzada instal·lada.
- pydot: Llibreria per generar gràfics de grafs i xarxes.
- graphviz: Paquet de programari per crear diagrames de grafs.

Assegura't d'instal·lar totes aquestes dependències abans de continuar amb el procés d'instal·lació.

## Instal·lació

1. Navega fins al directori del projecte utilitzant la comanda 'cd lambda-calcul'.
2. Assegura't de tenir totes les dependències necessàries instal·lades.
3. Executa la comanda 'make all' per posar en marxa el bot.
4. Obre l'aplicació de Telegram i envia un missatge a @LambdaCalculBot per iniciar una conversa amb ell.

## Autor

Nom del desenvolupador: Joan Caballero Castro
Correu electrònic: joan.caballero@estudiantat.upc.edu
