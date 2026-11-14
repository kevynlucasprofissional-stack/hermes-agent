# Reescrever arquitetura Hermes

**User:** Anonymous  
**Created:** 10/23/2026 1:49:49  
**Updated:** 10/23/2026 1:52:28  
**Exported:** 10/28/2026 0:51:44  
**Link:** [https://chatgpt.com/c/6adae76d-0e4c-83e9-8696-54e1f6e83c52](https://chatgpt.com/c/6adae76d-0e4c-83e9-8696-54e1f6e83c52)  

## Prompt:
23/10/2026, 01:50:05

devolve apenas mantendo a essência do texto, mantém a idéia central e em algum nível tenta manter também o tom de voz, mas torne o texto bem escrito, fácil de entender e sem redundâncias:

Você não entendeu eu tava em dúvida se script determinístico ou skill que é uma playbook com o mapa de Jason se é um ou se é outro fique em dúvidas sobre qualquer o certo ou se os dois funcionando junto é o melhor ou três né nesse caso o script deterministe com mais um mapa Json mais é a Skill barra playbook porque skill é meio que um playbook né tá você pode criar através de uma conexão com um browser dentro do Hermes o mapa do site do WhatsApp web e é isso você quiser você pode colocar isso colocar uma referência ao mapa da WhatsApp web na Skill Arms Work Ctrl só que a gente também tem que fazer isso no próprio Hermes sabe como atualmente as skills do Hermes são guardadas localmente acho que talvez a gente vai ter que inventar tipo umas skills globais que a gente vai salvar diretamente no código ponte do do Herm sabe sendo umas skills assim que a gente acha que todo mundo deveria ter ou umas skills que deveriam ser padrões do Hermes mesmo sabe guardar elas meio que junto com as capacidades operacionais se a gente não conseguir transformar elas em código né em capacidades determinísticas em capacidades operacionais se a gente não conseguir transformá elas em script e decidir que é melhor guardar como se fosse um skill com o mapa de Json ou se for fazer os três ou mais mapa Json mais script determinístico para funcionar melhor é ah não sei eu sei que tem que guardar tem que ser guardado no no código fonte do Hermes e não nos nos dados de aplicativo local isso tem que ser global tipo qualquer pessoa que faça um forque do meu Hermes tem que ter acesso a esses script e essa pessoa mesmo na primeira tarefa que ela for fazer se por acaso for uma tarefa com Whatsapp que o Armes dela Wermis Work dela consiga utilizar tão bem o WhatsApp web quanto o meu que tem essas skills tem essas capacidades operacionais tem esse mapa entendeu lembrando que a gente tem que colocar a função de auto aprimoramento para que sempre beleza a gente vai fornecer hoje um mapa do WhatsApp web só que a IA ela tem que ter ciência de que se alguma coisa no mapa muda ela tem que ir lá e atualizar o mapa dela entendeu é isso

## Response:
23/10/2026, 01:50:09 · gpt-6-thinking

**standard: **

Você não entendeu. Minha dúvida era justamente sobre qual abordagem é melhor: **um script determinístico, uma skill (que funciona como um playbook) com um mapa JSON, ou os três trabalhando juntos: script determinístico + mapa JSON + skill/playbook.** Não sei se existe uma abordagem mais correta ou se a combinação dessas três é a melhor solução.

Você pode utilizar uma conexão com o Browser do Hermes para explorar o WhatsApp Web e criar um mapa JSON do site. Se fizer sentido, pode incluir uma referência a esse mapa na skill **Hermes Work Ctrl**.

Mas precisamos pensar nisso também dentro da arquitetura do próprio Hermes.

Atualmente, pelo que entendo, as skills do Hermes são armazenadas localmente, nos dados do aplicativo. Talvez seja necessário criar uma categoria de **skills globais ou nativas**, armazenadas diretamente no código-fonte do Hermes, junto das capacidades operacionais.

A ideia é que determinadas skills, scripts, mapas JSON e capacidades operacionais sejam consideradas parte do próprio Hermes, porque são funcionalidades que qualquer instalação deveria possuir por padrão.

Por exemplo, se conseguirmos transformar uma skill em código determinístico, ótimo: ela passa a fazer parte das capacidades operacionais. Se não conseguirmos, ou se concluirmos que é melhor manter uma skill/playbook com um mapa JSON, também está tudo bem. E, se a melhor solução for combinar skill + mapa JSON + script determinístico, podemos fazer isso.

**O importante é que essas capacidades sejam incorporadas ao código-fonte do Hermes, e não fiquem restritas aos dados locais da minha instalação.**

Quero que qualquer pessoa que faça um fork do meu Hermes já tenha acesso a essas capacidades. Imagine alguém instalando o Hermes Work pela primeira vez: se a primeira tarefa dessa pessoa envolver o WhatsApp Web, o Hermes dela deverá conseguir operar o site com a mesma eficiência que o meu, aproveitando os scripts, as skills, os mapas JSON e as capacidades operacionais que já desenvolvemos.

E existe outro requisito fundamental: **o autoaprimoramento contínuo dessas capacidades.**

Hoje podemos fornecer um mapa completo do WhatsApp Web, mas esse mapa não pode ser tratado como algo permanente e imutável. A IA precisa compreender que, se o WhatsApp Web mudar sua estrutura, seus elementos ou seu comportamento, ela deverá identificar a mudança, investigar o que aconteceu e atualizar o mapa e, quando necessário, os scripts, as skills e os demais componentes relacionados.

Ou seja, não quero apenas entregar ao Hermes um conjunto de instruções para operar o WhatsApp Web. Quero que ele tenha **uma capacidade operacional nativa, compartilhável, reutilizável e capaz de evoluir continuamente**.

A solução precisa funcionar desde a primeira execução, estar disponível para qualquer instalação ou fork do Hermes e continuar melhorando conforme o próprio Hermes utiliza o WhatsApp Web.

**Em resumo, minha dúvida não é se devemos usar script determinístico, mapa JSON ou skill/playbook isoladamente. Quero que você avalie qual arquitetura - inclusive a combinação das três - oferece maior eficiência, confiabilidade, reutilização e capacidade de autoaprimoramento, e implemente essa solução como parte nativa do Hermes.**



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)