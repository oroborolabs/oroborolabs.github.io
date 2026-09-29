# Vigia de Ofertas

Robô que vigia o preço e a disponibilidade de páginas de produto e avisa no celular quando algo muda. É a demonstração pública da Oroboro Labs: a página ao vivo está em <https://oroborolabs.com/vigia-ofertas/>.

Usa só a biblioteca padrão do Python 3.12, sem instalar nada. Lê o preço do JSON-LD (schema.org Product/Offer) da página, com plano B pela meta `itemprop="price"`. Se não encontra preço, registra o erro e segue: nunca inventa valor.

## Como rodar local

```bash
cd vigia-ofertas
NTFY_TOPICO= python robo.py            # NTFY_TOPICO vazio = não envia aviso
```

Cada execução compara com `estado.json`, acrescenta uma linha em `historico.csv` quando o preço ou a disponibilidade mudou (ou na primeira leitura) e grava `ultimo_check.json`. Para testar o aviso, mude o preço em `produto-demo.html` e rode de novo.

## Como adaptar os alvos

Edite `alvos.json`, uma entrada por produto:

```json
[{"nome": "Meu produto", "url": "https://loja.exemplo/produto/123"}]
```

A página precisa trazer o preço em JSON-LD ou em `itemprop="price"`. Lojas que bloqueiam robôs (respondem 403) ou montam o preço só por JavaScript não funcionam com este método simples.

## Como assinar o aviso

Instale o app gratuito **ntfy** (Android ou iPhone), sem conta, e assine o tópico `oroborolabs-vigia-ofertas`, ou abra <https://ntfy.sh/oroborolabs-vigia-ofertas>. O tópico é público. Para usar o seu, defina a variável `NTFY_TOPICO` com um nome longo e difícil de adivinhar.

## Automático

O fluxo `.github/workflows/vigia-ofertas.yml` roda a cada 15 minutos no GitHub Actions e grava o histórico no repositório. Não precisa de segredo nenhum.
