// Gramàtica per la pràctica de lambda càlcul
grammar lc;
root : terme
     | definicio
     ;

terme : '(' terme ')'                       # parentesis
      | terme terme                         # aplicacio
      | ('λ' | '\\') variables '.' terme    # abstraccio
      | MACRO_TERME                         # macroTerme
      | terme MACRO_INF terme               # macroInfixa
      | VARIABLE                            # variable
      ;

macro : MACRO_TERME | MACRO_INF ;
definicio : macro ('≡' | '=') terme ;
variables : VARIABLE+ ;

VARIABLE : [a-z] ;
MACRO_TERME : [A-Z]+ [A-Z0-9]* ;
MACRO_INF : [*+-/!?%] ;

WS : [ \t\r\n]+ -> skip;
