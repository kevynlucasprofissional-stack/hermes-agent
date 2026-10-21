## Prompt para criar prompt para IA
De acordo com os anexos, faça o seguinte na branch feat/d049-browser-80-20-impl-20261018 , coloque instruções no primeiro prompt para sincronizar com a branch remota para as instruções que você vai fazer no repositório remoto usando o GitHub sejam acessíveis nas minhas pastas locais, no meu computador, e também me entregue me entregue um passo a passo, uma série de prompts que é o ponto ótimo entre economia de prompts e profundidade de qualidade de implementação, fazendo com que um prompt possa focar em um grupo de problemas simples que fazem sentido serem resolvidos juntos ou focar em um único problema complexo que requer atenção máxima da IA implementadora.

Atualize no repositório o roadmap.md, o jornal de engenharia, o hermes work inteligence e qualquer outro documento necessário com essas visões, descobertas e decisões que fizemos aqui.  
Agora cria um prompt para eu mandar para a IA que vai realizar essas implementações/ajustes e ela realizar esses pontos de melhoria que identificamos. Me vê um prompt para eu mandar e a IA resolver tudo isso. Cria um prompt que permita que a IA não precise pensar muito nem ficar lendo nada, que ele saiba de imediato o que ele tem que fazer, quando tem fazer, em que ordem e em que local. Para isso, leia todo o necessário direto no @GitHub  
De preferência, já crie o código que será utilizado nas implementações e correções, e já diga onde esse código será colocado ou qual parte do código esse novo código substitui, faça para que seja o máximo "plug and play" possível para que a IA implementadora pegue o seu código e já coloque nos lugares certos sendo necessário o minimo de adaptações ou ajustes para melhorar a integração.

Mas o prompt deve dar liberdade para a IA implementadora avaliar o código sugerido e melhorar ele ou adaptar conforme a necessidade, pedindo para a IA implementadora uma posição crítica e analítica para com sua sugestões (não tardando em aceitar caso a sua sugestão realmente for a melhor, mas não hesitando em adaptar ou ajustar caso ela encontre uma opção ainda melhor), e também uma posição de implementadora, ou seja, de realmente trabalhar as mudanças no código fonte do Hermes Work / Agent afim de evoluir na direção proposta.

Coloque no prompt instruções para a IA implementadora conferir constamente e conforme necessidade o código das referências para criar/ajustar o código do Hermes Work
O caminho das referências é o seguinte: C:\Github\hermes-agent\referências

## Juntar tudo no main
Precisamos juntar essas alterações no main e sincronizar o main local com o main remoto (Main na nuvem do github).
Resolve conflitos, faz os commits, pull request, merge, sincroniza e junta tudo no main.

ou

Faça uma consolidação completa do repositório, deixando o `main` como a única fonte canônica, atualizada e sincronizada entre o ambiente local e o Git remoto.

Primeiro, inspecione o estado completo do repositório antes de alterar qualquer coisa: branches locais e remotas, Pull Requests abertos, Draft PRs, commits divergentes, alterações não commitadas, branches que estejam à frente ou atrás do `main`, merges pendentes e quaisquer outras divergências entre versões.

Em seguida:

1. Identifique todas as alterações válidas que ainda não chegaram ao `main`.
    
2. Compare branches e Pull Requests para evitar duplicar trabalho ou sobrescrever implementações mais recentes.
    
3. Resolva todos os conflitos de merge preservando a implementação mais completa, atual e compatível com a arquitetura existente.
    
4. Quando duas branches implementarem soluções diferentes para o mesmo problema, analise o código e consolide a melhor solução em vez de simplesmente escolher uma versão.
    
5. Integre ao `main` tudo o que estiver concluído e fizer sentido manter.
    
6. Resolva também Pull Requests e Draft PRs pendentes, incorporando ao `main` o trabalho aproveitável que ainda não esteja presente nele.
    
7. Verifique se existem commits órfãos, branches não incorporadas ou mudanças importantes que poderiam ser perdidas durante a consolidação.
    
8. Execute os testes, builds, linters ou demais validações existentes no projeto após os merges e corrija problemas introduzidos pela consolidação.
    
9. Só considere uma branch obsoleta ou descartável depois de confirmar que nenhuma alteração exclusiva e relevante dela será perdida.
    
10. Depois da consolidação, atualize o `main` remoto e sincronize novamente o `main` local com o remoto, garantindo que ambos apontem para o mesmo estado final.
    

Ao terminar, o repositório deve estar em um estado limpo e coerente:

- `main` local e `main` remoto sincronizados;
    
- nenhuma implementação válida perdida;
    
- nenhuma divergência relevante ainda presa em outra branch;
    
- conflitos resolvidos;
    
- Pull Requests e Draft PRs tratados;
    
- alterações importantes consolidadas;
    
- working tree limpa;
    
- projeto validado pelos testes disponíveis.
    

Não faça merges cegos, não use `force push` destrutivo e não descarte código apenas para eliminar conflitos. Preserve o histórico sempre que possível e priorize integridade do código e ausência de regressões.

Antes de finalizar, faça uma última auditoria comparando novamente `main`, branches locais, branches remotas e PRs para confirmar que nenhuma mudança relevante ficou para trás.

No final, apresente um resumo objetivo contendo:

- o que foi incorporado ao `main`;
    
- quais conflitos foram encontrados e como foram resolvidos;
    
- quais branches/PRs foram encerrados ou considerados obsoletos;
    
- quais validações foram executadas;
    
- o commit final do `main`;
    
- confirmação de que local e remoto estão sincronizados.

## Para analisar trabalho
Ok, ajustes feitos. Faz uma análise profunda da qualidade do trabalho realizado, está disponível no @GitHub , mas não fique preso só em melhorar o código atual, vê o que está ótimo, o que está ok, sugira corrigir o que for um erro crítico, mas se tiver erros simples que não afetam o fluxo geral do funcionamento, sugira passar para as próximas implementações. Precisamos corrigir o que for inaceitável, aceitar erros aceitáveis e partir para os próximos passos (Se é que existem erros aceitáveis).

## Para reescrever o texto
Mantém a essência do texto, mantém a idéia central e em algum nível tenta manter também o tom de voz, mas torne o texto bem escrito, fácil de entender e sem redundâncias:

# Outros

Prompt 01

De acordo com o que leu, de acordo com o trabalho já feito, de acordo com as referências, de acordo com a auditoria code to code já realizada, quais os próximos passos de maior impacto agora?

Prompt 02

De acordo com o anexo, crie um prompt pronto para eu te enviar e você começar a fazer tudo. O ideal é que faça tudo de uma vez, mas já que é improvável que faça isso, coloque instruções para sempre quando a IA for parar te trabalhar, que ela me retorne um prompt para eu copiar e colar e a IA continue o trabalho exatamente do local certo, com as instruções corretas, guiando ela para ao final de tudo nós realizarmos esse plano do anexo com perfeição.

Prompt 03:

Faça de acordo com o texto colado.
Para isso use:

@github
@remote desktop commander
@superpowers
@community-agent-workflows

Prompt 04:

Primeiro, através de @github e @remote-desktop-commander inspecione o diretório / repositório do Hermes Agente e crie um plano de como implementar com perfeição esses 3 pontos, crie critério de aceite a nível MVP, queremos que as implementações funcionem, mas não queremos aprofundar nisso ao infinito. Queremos fazer apenas o 20% de trabalho que gere 80% de resultado.

## Análise comparativa de repositório

Vamos fazer agora uma análise crítica e comparativa sempre olhando para o lado de melhorar o Hermes Work, e dessa vez vamos focar essa sessão em melhorar o browser nativo dele.

Já observamos a arquitetura como está, mas vamos observar a arquitetura usando também pontos de referência pelo quais podemos comparar.

Vou te dar um repositório e você vai comparar o repositório com o atual browser do Hermes Work, procurando onde o Browser do Hermes Work é pior, onde é melhor, onde o Hermes Work pode se inspirar para melhorar o seu próprio código, onde o ele pode copiar o código completo para dentro do Hermes Work (Tenho permissão para isso em todos os repositórios), onde ele pode pegar código para fazer uma versão adaptada do Hermes pois isso vai beneficiar o Hermes e fazer ele evoluir como produto.

Além disso, eu gostaria que nesses repositórios que vou ir indicando, que você separasse um momento para procurar oportunidades específicar de melhorar economia de tokens, velocidade do Browser, e objetividade da IA em utilizar ele (Não precisar ficar pesquisando ou criando ferramentas para conseguir usar o Browser com velocidade, qualidade e facilidade). Quero que faça isso estudando o código fonte do Hermes Work e o do repositório que indiquei para a comparação, estudo e pesquisa.

Segue o repositório: