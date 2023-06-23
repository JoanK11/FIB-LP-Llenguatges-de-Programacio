from __future__ import annotations
import html
from telegram.ext import InlineQueryHandler
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram import Update
import logging
import uuid
import pydot
from dataclasses import dataclass

from antlr4 import *
from lcLexer import lcLexer
from lcParser import lcParser
from lcVisitor import lcVisitor

# ---- Tasca 2: el visitador ----


@dataclass
class Variable:
    val: str


@dataclass
class Aplicacio:
    esq: Arbre
    dre: Arbre


@dataclass
class Abstraccio:
    cap: str
    cos: Arbre


Arbre = Variable | Abstraccio | Aplicacio


class TreeVisitor(lcVisitor):
    def __init__(self, macros={}):
        self.taula = macros

    def visitRoot(self, ctx):
        [terme] = list(ctx.getChildren())
        return self.visit(terme)

    def visitParentesis(self, ctx):
        [p1, terme, p2] = list(ctx.getChildren())
        return self.visit(terme)

    def visitAplicacio(self, ctx):
        [termeEsq, termeDre] = list(ctx.getChildren())
        return Aplicacio(self.visit(termeEsq), self.visit(termeDre))

    def visitAbstraccio(self, ctx):
        [op1, cap, op2, cos] = list(ctx.getChildren())
        t = self.visit(cos)
        for var in reversed(self.visit(cap)):
            t = Abstraccio(var, t)
        return t

    def visitDefinicio(self, ctx):
        [macro, op, terme] = list(ctx.getChildren())
        self.taula[macro.getText()] = self.visit(terme)
        return None  # Retornem None per diferenciar quan fem una definició

    def visitVariables(self, ctx):
        vars = list(ctx.getChildren())
        r = ''.join([var.getText() for var in vars])
        return r

    def visitVariable(self, ctx):
        [var] = list(ctx.getChildren())
        return Variable(var.getText())

    def visitMacro(self, ctx):
        [macro] = list(ctx.getChildren())
        return self.taula[macro.getText()]

    def visitMacroTerme(self, ctx):
        return self.visitMacro(ctx)

    def visitMacroInfixa(self, ctx):
        [terme1, macroInfixa, terme2] = list(ctx.getChildren())
        arbreMacro = self.taula[macroInfixa.getText()]
        return Aplicacio(Aplicacio(arbreMacro, self.visit(terme1)), self.visit(terme2))


def getArbreSemantic(arbreSemantic: Arbre) -> str:
    """
    Retorna la representació en cadena de caràcters de l'arbre semàntic.

    Paràmetres:
        arbreSemantic (Arbre): L'arbre semàntic a processar.

    Retorn:
        str: La representació en cadena de caràcters de l'arbre semàntic.
    """
    match arbreSemantic:
        case Variable(val):
            return val

        case Aplicacio(esq, dre):
            str_esq = getArbreSemantic(esq)
            str_dre = getArbreSemantic(dre)
            return '(' + str_esq + str_dre + ')'

        case Abstraccio(cap, cos):
            str_cos = getArbreSemantic(cos)
            return '(λ' + cap + '.' + str_cos + ')'

# ---- Tasca 3: avaluador ----


def cercarVarConflictiva(arbre: Arbre, var: str) -> bool:
    """
    Comprova si la variable 'var' es troba a l'arbre 'arbre'.

    Paràmetres:
        arbre (Arbre): L'arbre en el qual es vol cercar la variable.
        var (str): La variable que es busca.

    Retorn:
        bool: Cert si es troba la variable, Fals si no es troba.
    """
    match arbre:
        case Variable(val):
            return val == var

        case Aplicacio(esq, dre):
            return cercarVarConflictiva(esq, var) or cercarVarConflictiva(dre, var)

        case Abstraccio(cap, cos):
            return cercarVarConflictiva(cos, var)


def generarNovaVariable(varVistes: set) -> str:
    """
    Genera una nova variable que no es troba en el conjunt de variables 'varVistes'.

    Paràmetres:
        varVistes (set): Conjunt de variables ja utilitzades.

    Retorn:
        str: Nova variable que no està en 'varVistes'.
    """
    i = 25
    while i >= 0:
        novaVar = chr(ord('a') + i)
        if novaVar not in varVistes:
            return novaVar
        i -= 1


def obtenirVariables(arbre: Arbre) -> set:
    """
    Retorna un conjunt amb totes les variables de l'arbre passat com a paràmetre.

    Paràmetres:
        arbre (Arbre): L'arbre del qual s'obtenen les variables.

    Retorn:
        set: Conjunt que conté totes les variables de l'arbre.
    """
    match arbre:
        case Variable(val):
            return {val}

        case Aplicacio(esq, dre):
            varsEsq = obtenirVariables(esq)
            varsDre = obtenirVariables(dre)
            return varsEsq | varsDre

        case Abstraccio(cap, cos):
            return obtenirVariables(cos)


def cercarAbstraccions(arbre: Arbre, cap: str, varsConfl: set, varsVistes: set):
    """
    Cerca abstraccions en l'arbre donat i realitza alpha-conversions si es produeixen conflictes.

    Paràmetres:
        arbre (Arbre): L'arbre en el qual es vol cercar abstraccions.
        cap (str): El valor de la variable lligada de l'abstracció que s'està cercant.
        varsConfl (set): Conjunt de variables amb les quals es poden produir conflictes.
        varsVistes (set): Conjunt de totes les variables utilitzades en l'arbre.

    Retorn:
        Arbre: L'arbre modificat després de realitzar les alpha-conversions, si és necessari.
        str: El valor de l'antiga variable lligada que ha estat substituïda, o None si no hi ha hagut substitució.
        str: El valor de la nova  variable lligada que ha estat substituïda, o None si no hi ha hagut substitució.
    """
    match arbre:
        case Variable(_):
            return arbre, None, None

        case Aplicacio(esq, dre):
            novaEsq, antigaVarEsq, novaVarEsq = cercarAbstraccions(esq, cap, varsConfl, varsVistes)
            # He decidit separar les alpha-conversions de les aplicacions en dos passos.
            # Així puc mostrar les dues alpha-conversions per separat, en cas que hi hagi.
            if antigaVarEsq:
                return Aplicacio(novaEsq, dre), antigaVarEsq, novaVarEsq
            else:
                novaDre, antigaVarDre, novaVarDre = cercarAbstraccions(dre, cap, varsConfl, varsVistes)
                return Aplicacio(esq, novaDre), antigaVarDre, novaVarDre

        case Abstraccio(cap2, cos):
            if cap2 in varsConfl:
                conflicte = cercarVarConflictiva(cos, cap)
                # Es produeix conflicte quan tenim una abstracció amb un cap que pertany a 'varsConfl',
                # i en el cos de l'abstracció es troba la variable 'cap' passada per paràmetre.
                if conflicte:
                    nouCap2 = generarNovaVariable(varsVistes)
                    alphaCos = substitueixVariable(cos, cap2, Variable(nouCap2))
                    varsVistes = varsVistes | {nouCap2}
                    return Abstraccio(nouCap2, alphaCos), cap2, nouCap2
                else:
                    nouCos, antigaVar, novaVar = cercarAbstraccions(cos, cap, varsConfl, varsVistes)
                    return Abstraccio(cap2, nouCos), antigaVar, novaVar
            else:
                nouCos, antigaVar, novaVar = cercarAbstraccions(cos, cap, varsConfl, varsVistes)
                return Abstraccio(cap2, nouCos), antigaVar, novaVar


async def alphaConversio(abstr: Abstraccio, aplDre: Arbre, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Realitza una alpha-conversió si és necessària a una abstracció, basada en l'arbre de la dreta de l'aplicació.

    Paràmetres:
        abstr (Abstraccio): L'abstracció a la qual es pot aplicar l'alpha-conversió.
        aplDre (Arbre): L'arbre de la dreta de l'aplicació.
        update (Update): L'actualització de Telegram per respondre amb el resultat de l'alpha-conversió.
        context (ContextTypes.DEFAULT_TYPE): El context de l'execució de la conversa de Telegram.

    Retorn:
        Abstraccio: L'abstracció modificada després de l'alpha-conversió, si és necessària.
        bool: Cert si s'ha realitzat una alpha-conversió, Fals si no s'ha realitzat cap alpha-conversió.
    """
    varsDre = obtenirVariables(aplDre)
    varsVistes = obtenirVariables(abstr) | varsDre
    nouCos, antigaVar, novaVar = cercarAbstraccions(abstr.cos, abstr.cap, varsDre, varsVistes)

    if antigaVar:
        novaAbstr = Abstraccio(abstr.cap, nouCos)
        str_abstr = getArbreSemantic(abstr)
        str_novaAbstr = getArbreSemantic(novaAbstr)

        if context.user_data['mostrar_conversions']:
            await update.message.reply_text(str_abstr + ' → α(' + antigaVar + '→' + novaVar + ') → ' + str_novaAbstr)
        return novaAbstr, True

    else:
        return abstr, False


def substitueixVariable(arbre: Arbre, var: str, subst: Arbre) -> Arbre:
    """
    Substitueix totes les ocurrences de la variable 'var' per l'arbre de substitució 'subst' en l'arbre donat.

    Paràmetres:
        arbre (Arbre): L'arbre en el qual es vol realitzar la substitució.
        var (str): La variable que es vol substituir.
        subst (Arbre): L'arbre de substitució que s'utilitzarà en lloc de la variable.

    Retorn:
        Arbre: L'arbre modificat després de realitzar la substitució.
    """
    match arbre:
        case Variable(val):
            if val == var:
                return subst
            else:
                return arbre

        case Aplicacio(esq, dre):
            termeEsq = substitueixVariable(esq, var, subst)
            termeDre = substitueixVariable(dre, var, subst)
            return Aplicacio(termeEsq, termeDre)

        case Abstraccio(cap, cos):
            terme = substitueixVariable(cos, var, subst)
            return Abstraccio(cap, terme)


async def betaReduccio(abstr: Abstraccio, subst: Arbre, arbreAntic: Arbre, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Arbre:
    """
    Realitza una beta reducció substituint la variable 'abstr.cap' per l'arbre 'subst' en 'abstr.cos'.

    Paràmetres:
        abstr (Abstraccio): L'abstracció en la qual es realitzarà la beta reducció.
        subst (Arbre): L'arbre de substitució que s'utilitzarà en lloc de la variable 'abstr.cap'.
        arbreAntic (Arbre): L'arbre original abans de la beta reducció.
        update (Update): L'actualització de Telegram per respondre amb el resultat de la beta reducció.
        context (ContextTypes.DEFAULT_TYPE): El context de l'execució de la conversa de Telegram.

    Retorn:
        Arbre: L'arbre modificat després de realitzar la beta reducció.
    """
    nouArbre = substitueixVariable(abstr.cos, abstr.cap, subst)
    str_arbreAntic = getArbreSemantic(arbreAntic)
    str_nouArbre = getArbreSemantic(nouArbre)

    if context.user_data['mostrar_reduccions']:
        await update.message.reply_text(str_arbreAntic + ' →β→ ' + str_nouArbre)
    return nouArbre


async def evalArbreSemantic(arbre: Arbre, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Avalua un arbre semàntic realitzant les alpha-conversions i beta reduccions necessàries.

    Paràmetres:
        arbre (Arbre): L'arbre semàntic a avaluar.
        update (Update): L'actualització de Telegram per respondre amb els passos d'avaluació.
        context (ContextTypes.DEFAULT_TYPE): El context de l'execució de la conversa de Telegram.

    Retorn:
        Arbre: L'arbre modificat després de l'avaluació.
        bool: Booleà que indica si s'ha realitzat una alpha-conversió.
        bool: Booleà que indica si s'ha realitzat una beta reducció.
    """
    match arbre:
        case Abstraccio(cap, cos):
            nouCos, alphaConv, betaRed = await evalArbreSemantic(cos, update, context)
            return Abstraccio(cap, nouCos), alphaConv, betaRed

        case Aplicacio(esq, dre):
            if isinstance(esq, Abstraccio):
                novaEsq, alphaConv = await alphaConversio(esq, dre, update, context)
                if alphaConv:
                    return Aplicacio(novaEsq, dre), True, False
                else:
                    return await betaReduccio(esq, dre, arbre, update, context), False, True
            else:
                termeEsq, alphaConvEsq, betaRedEsq = await evalArbreSemantic(esq, update, context)
                if alphaConvEsq or betaRedEsq:
                    return Aplicacio(termeEsq, dre), alphaConvEsq, betaRedEsq
                else:
                    termeDre, alphaConvDre, betaRedDre = await evalArbreSemantic(dre, update, context)
                    return Aplicacio(esq, termeDre), alphaConvDre, betaRedDre

        case Variable(_):
            return arbre, False, False

# ---- Tasca 7: representació gràfica dels arbres ----


async def printImatgeArbreSemantic(arbreSemantic: Arbre, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Genera una imatge que representa visualment l'arbre semàntic i l'envia com a resposta a l'usuari.

    Paràmetres:
        arbreSemantic (Arbre): L'arbre semàntic que es vol representar.
        update (Update): L'objecte Update de Telegram que representa el missatge de l'usuari.
        context (ContextTypes.DEFAULT_TYPE): El context de l'execució de la conversa de Telegram.
    """
    # Definim el graf que representarà l'arbre semàntic
    graph = pydot.Dot(graph_type='digraph')

    def createNodeRec(node: Arbre, pare: Arbre = None, pare_id: str = None, mapa_variables={}) -> None:
        """
        Funció recursiva per crear els nodes i les arestes del graf a partir de l'arbre semàntic.

        Paràmetres:
            node (Arbre): El node actual de l'arbre semàntic.
            pare (Arbre): El node pare del node actual.
            pare_id (str): L'identificador del node pare en el graf.
            mapa_variables (dict): Un diccionari que mapeja les variables als seus identificadors en el graf.
        """
        node_id = str(uuid.uuid1())

        match node:
            case Variable(val):
                label = val

            case Aplicacio(esq, dre):
                label = '@'
                createNodeRec(esq, node, node_id, mapa_variables)
                createNodeRec(dre, node, node_id, mapa_variables)

            case Abstraccio(cap, cos):
                label = 'λ' + cap
                mapa_variables[cap] = node_id
                createNodeRec(cos, node, node_id, mapa_variables)

        nouNode = pydot.Node(node_id, label=label, shape='plaintext')
        graph.add_node(nouNode)

        if pare:
            graph.add_edge(pydot.Edge(pare_id, nouNode))

        if isinstance(node, Variable):
            cap = mapa_variables.get(node.val)
            if cap:
                edge = pydot.Edge(cap, nouNode, style='dotted', dir='back')
                graph.add_edge(edge)

    # Processem l'arbre
    createNodeRec(arbreSemantic)

    # Carreguem i enviem la imatge
    graph.write_png('output.png')
    photo_file = open('output.png', 'rb')
    await update.message.reply_photo(photo_file)

# ---- Tasca 6: AChurch a Telegram ----

TOKEN = open('token.txt').read().strip()
"""
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)"""


def initialize(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Inicialitza les dades de context per a l'execució del bot.

    Paràmetres:
        context (ContextTypes.DEFAULT_TYPE): El context de l'execució de la conversa de Telegram.
    """
    # Inicialitzacions del context.user_data
    context.user_data['macros'] = {}
    context.user_data['max_reduccions'] = 10
    context.user_data['mostrar_conversions'] = True
    context.user_data['mostrar_reduccions'] = True
    context.user_data['mostrar_estadistiques'] = True
    context.user_data['mostrar_imatges'] = True
    context.user_data['macros_importades'] = False

    # Inicialitzacions del context.bot_data
    if not 'estat' in context.bot_data:
        context.bot_data['estat'] = 'sense estat :('


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Respon a la comanda /start de l'usuari mostrant un missatge de benvinguda i informació sobre el bot.

    Paràmetres:
        update (Update): L'objecte Update de Telegram que representa el missatge d'inici.
        context (ContextTypes.DEFAULT_TYPE): El context de l'execució de la conversa de Telegram.
    """
    if not 'estat' in context.bot_data:
        initialize(context)

    estat_html = html.escape(context.bot_data['estat'])

    await update.message.reply_html('Benvingut a LambdaCalculBot ' + update.message.chat.first_name + '!\n'
                                    'Soc un bot que avalua expressions en lambda càlcul.\n\n'
                                    'Actualment estic ' + estat_html + '.\n' + "Pots canviar el meu estat que és compartit amb la resta d'usuaris amb la comanda <code>/set estat &lt;nou_estat&gt;</code>.\n\n"
                                    'Escriu /help per veure totes les comandes que accepto.')


async def author(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Respon a la comanda /author de l'usuari amb informació sobre l'autor del bot i una fotografia seva.

    Paràmetres:
        update (Update): L'objecte Update de Telegram que representa el missatge de l'usuari.
        context (ContextTypes.DEFAULT_TYPE): El context de l'execució de la conversa de Telegram.
    """
    await update.message.reply_text('El meu creador és Joan Caballero Castro.\n'
                                    "M'ha creat amb molt de carinyo <3.\n")
    photo_file = open('foto.jpg', 'rb')
    await update.message.reply_photo(photo_file)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Respon a la comanda /help de l'usuari amb un missatge d'ajuda que descriu les comandes disponibles del bot.

    Paràmetres:
        update (Update): L'objecte Update de Telegram que representa el missatge de l'usuari.
        context (ContextTypes.DEFAULT_TYPE): El context de l'execució de la conversa de Telegram.
    """
    await update.message.reply_text(
        '/start: Et dono un missatge de benvinguda.\n'
        "/author: Et proporciono informació sobre el meu creador.\n"
        "/help: Et mostro aquest missatge d'ajuda.\n"
        "/macros: T'ensenyo les macros que has definit.\n"
        '/importar_macros: Importa macros per defecte.\n'
        "/config: Et mostro tota la meva configuració actual.\n"
        '/set: Et permet modificar la meva configuració actual.\n'
        '         Escriu /set per veure totes les opcions disponibles.\n'
        'Expressió λ-càlcul.')


async def macros(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Respon a la comanda /macros de l'usuari amb la llista de macros que ha definit.

    Paràmetres:
        update (Update): L'objecte Update de Telegram que representa el missatge de l'usuari.
        context (ContextTypes.DEFAULT_TYPE): El context de l'execució de la conversa de Telegram.
    """
    if not 'macros' in context.user_data:
        initialize(context)

    taula_macros = context.user_data['macros']
    macrosSize = len(taula_macros)
    if macrosSize == 0:
        message = "L'usuari " + update.message.chat.first_name + ' encara no té cap macro definida ☹️.\n' \
                  'Vinga, defineix una macro que no costa res!'
    else:
        message = "L'usuari " + update.message.chat.first_name + ' ha definit ' + str(macrosSize) + ' macros 😄:\n'
        for key, value in taula_macros.items():
            message += '   ' + key + ' ≡ ' + getArbreSemantic(value) + '\n'

    await update.message.reply_text(message)


async def config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Respon a la comanda /config de l'usuari amb les configuracions actualment definides.

    Paràmetres:
        update (Update): L'objecte Update de Telegram que representa el missatge de l'usuari.
        context (ContextTypes.DEFAULT_TYPE): El context de l'execució de la conversa de Telegram.
    """
    if not 'macros' in context.user_data:
        initialize(context)

    message = 'A continuació et mostro les configuracions que tens definides:\n\n'

    message += '<b>max_reduccions</b> = ' + str(context.user_data['max_reduccions']) + \
        '  - Defineix el nombre màxim de beta reduccions per avaluació.\n'
    message += '<b>mostrar_conversions</b> = ' + str(context.user_data['mostrar_conversions']) + \
        '  - Mostra/Amaga les alpha conversions.\n'
    message += '<b>mostrar_reduccions</b> = ' + str(context.user_data['mostrar_reduccions']) + \
        '  - Mostra/Amaga les beta reduccions.\n'
    message += '<b>mostrar_estadistiques</b> = ' + str(context.user_data['mostrar_estadistiques']) + \
        '  - Mostra/Amaga les estadístiques de cada avaluació.\n'
    message += '<b>mostrar_imatges</b> = ' + str(context.user_data['mostrar_imatges']) + \
        '  - Mostra/Amaga les imatges de cada avaluació.\n'
    message += '<b>importar_macros</b> = ' + str(context.user_data['macros_importades']) + \
        '  - Importa un conjunt de macros per defecte.\n'
    estat_html = html.escape(context.bot_data['estat'])
    message += '<b>estat</b> = ' + estat_html + \
        '  - Defineix el meu estat que és compartit per tots els usuaris.'

    await update.message.reply_html(message)


async def set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Actualitza la configuració del bot basant-se en els arguments proporcionats per l'usuari en la comanda /set.

    Paràmetres:
        update (Update): L'objecte Update de Telegram que representa el missatge de l'usuari.
        context (ContextTypes.DEFAULT_TYPE): El context de l'execució de la conversa de Telegram.
    """
    if not 'macros' in context.user_data:
        initialize(context)

    try:
        conf = context.args[0]
        if conf == 'max_reduccions':
            n = int(context.args[1])
            if n < 1:
                await update.message.reply_html('<b>ERROR:</b> El nombre màxim de beta reduccions ha de ser major a 0.')
                return
            context.user_data[conf] = n
            await update.message.reply_text("El nombre màxim de beta reduccions s'ha establert a " + str(n) + '.')

        elif conf in ['mostrar_conversions', 'mostrar_reduccions', 'mostrar_estadistiques', 'mostrar_imatges']:
            b = context.args[1]
            conf_mapping = {
                'mostrar_conversions': 'alpha conversions.',
                'mostrar_reduccions': 'beta reduccions.',
                'mostrar_estadistiques': "estadístiques després d'avaluar una expressió.",
                'mostrar_imatges': 'imatges de cada avaluació.'
            }

            if b == 'si':
                context.user_data[conf] = True
                await update.message.reply_text('Es mostraran les ' + conf_mapping.get(conf))
            elif b == 'no':
                context.user_data[conf] = False
                await update.message.reply_text('No es mostraran les ' + conf_mapping.get(conf))
            else:
                await update.message.reply_html('<b>Usage:</b> /set ' + conf + ' {si/no}')

        elif conf == 'estat':
            estat = ' '.join(context.args[1:])
            context.bot_data[conf] = estat
            await update.message.reply_text('Ara estic ' + estat + '.')

        else:
            raise ValueError()

    except (IndexError, ValueError):
        await update.message.reply_html('<b>--- Usage ---</b>\n'
                                        '   /set max_reduccions &lt;num_reduccions&gt;\n'
                                        '   /set mostrar_conversions {si/no}\n'
                                        '   /set mostrar_reduccions {si/no}\n'
                                        '   /set mostrar_estadistiques {si/no}\n'
                                        '   /set mostrar_imatges {si/no}\n'
                                        "   /set estat &lt;nou_estat (visible per la resta d'usuaris)&gt;")


async def importar_macros(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Importa una sèrie de macros per defecte al conjunt de macros de l'usuari.

    Paràmetres:
        update (Update): L'objecte Update de Telegram que representa el missatge de l'usuari.
        context (ContextTypes.DEFAULT_TYPE): El context de l'execució de la conversa de Telegram.
    """
    if not 'macros' in context.user_data:
        initialize(context)

    if not context.user_data['macros_importades']:
        macros_importades = ['TRUE=λx.λy.x', 'FALSE=λx.λy.y', 'AND=λab.ab(λxy.y)',
                             'OR=λab.a(λxy.x)b', 'NOT=λa.a(λb.λc.c)(λd.λe.d)',
                             'N2=λs.λz.s(s(z))', 'N3=λs.λz.s(s(s(z)))', 'SUCC=λa.λb.λc.b(abc)',
                             '+=λp.λq.λx.λy.(px(qxy))', 'TWICE=λf.λx.f(fx)', 'ID=λx.x',
                             'Y=λy.(λx.y(xx))(λx.y(xx))']

        visitor = TreeVisitor(context.user_data['macros'])
        for macro in macros_importades:
            input_stream = InputStream(macro)
            lexer = lcLexer(input_stream)
            token_stream = CommonTokenStream(lexer)
            parser = lcParser(token_stream)
            tree = parser.root()
            visitor.visit(tree)

        context.user_data['macros_importades'] = True
        await update.message.reply_text('Macros importades correctament.\nEscriu /macros per veure les noves macros.')
    else:
        await update.message.reply_text('Ja vas importar les macros i les tens disponibles a /macros.')


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Processa i avalua una expressió en lambda càlcul i retorna el resultat.

    Paràmetres:
        update (Update): L'objecte Update de Telegram que representa el missatge de l'usuari.
        context (ContextTypes.DEFAULT_TYPE): El context de l'execució de la conversa de Telegram.
    """
    if not 'macros' in context.user_data:
        initialize(context)

    # Configuració
    visitor = TreeVisitor(context.user_data['macros'])
    msg = update.message.text
    input_stream = InputStream(msg)
    lexer = lcLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = lcParser(token_stream)
    tree = parser.root()

    if parser.getNumberOfSyntaxErrors() == 0:
        arbreSemantic = visitor.visit(tree)

        # Si hem fet una definició no cal avaluar l'arbre
        if arbreSemantic == None:
            await update.message.reply_text('Macro definida correctament.')
            return

        str_arbre = getArbreSemantic(arbreSemantic)
        await update.message.reply_text(str_arbre)

        if context.user_data['mostrar_imatges']:
            await printImatgeArbreSemantic(arbreSemantic, update, context)

        maxBetaReduccions = context.user_data['max_reduccions']
        nAlpha, nBeta = 0, 0
        nouArbre, alphaConv, betaRed = await evalArbreSemantic(arbreSemantic, update, context)
        if alphaConv:
            nAlpha += 1
        elif betaRed:
            nBeta += 1
            maxBetaReduccions -= 1

        while (alphaConv or betaRed) and maxBetaReduccions > 0:
            nouArbre, alphaConv, betaRed = await evalArbreSemantic(nouArbre, update, context)
            if alphaConv:
                nAlpha += 1
            elif betaRed:
                nBeta += 1
                maxBetaReduccions -= 1

        if maxBetaReduccions <= 0:
            await update.message.reply_text('...')
            await update.message.reply_html("S'ha arribat al màxim de beta reduccions (" + str(nBeta) + ').')
            await update.message.reply_html('Utilitza la comanda <code>/set max_reduccions &lt;num_reduccions&gt;</code> per incrementar el límit de beta reduccions.')
            await update.message.reply_text('Arbre resultant després de ' + str(nBeta) + ' beta reduccions:')

        if nAlpha or nBeta:
            str_nouArbre = getArbreSemantic(nouArbre)
            await update.message.reply_html('<b>' + str_nouArbre + '</b>')

            if context.user_data['mostrar_imatges']:
                await printImatgeArbreSemantic(nouArbre, update, context)

            if context.user_data['mostrar_estadistiques']:
                await update.message.reply_html("<b>Estadístiques:</b>\n   N. alpha conversions: " + str(nAlpha) + '\n   N. beta reduccions: ' + str(nBeta))
    else:
        await update.message.reply_html('<b>ERROR DE SINTAXIS\n</b>Hi ha ' + str(parser.getNumberOfSyntaxErrors()) + " errors de sintaxi. No s'ha pogut avaluar l'expressió.")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gestiona les comandes no reconegudes pel bot.

    Paràmetres:
        update (Update): L'objecte Update de Telegram que representa el missatge de l'usuari.
        context (ContextTypes.DEFAULT_TYPE): El context de l'execució de la conversa de Telegram.
    """
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Ho sento, no he entès aquesta comanda.')


if __name__ == '__main__':
    """
    Funció principal que inicialitza i executa el bot.

    La funció crea una instància de l'ApplicationBuilder i afegeix els gestors de comandes i missatges.
    També executa el bot fins que es premi CTRL+C.

    """
    application = ApplicationBuilder().token(TOKEN).build()

    # Commands
    start_handler = CommandHandler('start', start)
    author_handler = CommandHandler('author', author)
    help_handler = CommandHandler('help', help)
    macros_handler = CommandHandler('macros', macros)
    config_handler = CommandHandler('config', config)
    set_handler = CommandHandler('set', set)
    importar_macros_handler = CommandHandler('importar_macros', importar_macros)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)

    # Handlers
    application.add_handler(start_handler)
    application.add_handler(author_handler)
    application.add_handler(help_handler)
    application.add_handler(macros_handler)
    application.add_handler(config_handler)
    application.add_handler(set_handler)
    application.add_handler(importar_macros_handler)
    application.add_handler(echo_handler)

    # Others (This handler must be added last)
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    application.add_handler(unknown_handler)

    # Runs the bot until you hit CTRL+C
    application.run_polling()
