#!/bin/bash

# Nomes e configurações
CONTAINER_NAME="mysql-flike"
VOLUME_NAME="mysql-flike"
MYSQL_IMAGE="mysql:latest"

# Variáveis do banco (lidas do ambiente ou definidas diretamente)
DB_HOST="localhost"
DB_USER="admin"
DB_PASSWORD="admin123"
DB_DATABASE="flike"
DB_PORT="5469"

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # Sem cor

error_exit() {
    echo -e "${RED}Erro: $1${NC}" >&2
    exit 1
}

# Verifica Docker
if ! command -v docker &> /dev/null; then
    error_exit "Docker não encontrado. Instale o Docker e tente novamente."
fi

if ! docker info &> /dev/null; then
    error_exit "Docker não está em execução. Inicie o serviço do Docker."
fi

# Remove container anterior se existir
if [ "$(docker ps -aq -f name=^/${CONTAINER_NAME}$)" ]; then
    echo "Container '$CONTAINER_NAME' já existe. Removendo..."
    docker stop "$CONTAINER_NAME" >/dev/null
    docker rm "$CONTAINER_NAME" >/dev/null
fi

# Executa o container MySQL (sem comentários após as barras)
echo "Iniciando container MySQL..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -e MYSQL_ROOT_PASSWORD="rootpass123" \
    -e MYSQL_DATABASE="$DB_DATABASE" \
    -e MYSQL_USER="$DB_USER" \
    -e MYSQL_PASSWORD="$DB_PASSWORD" \
    -p "$DB_PORT":3306 \
    -v "$VOLUME_NAME":/var/lib/mysql \
    --restart unless-stopped \
    "$MYSQL_IMAGE"

# Verifica se o container iniciou
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Container MySQL iniciado com sucesso!${NC}"
    echo "Detalhes da conexão:"
    echo "  Host: $DB_HOST"
    echo "  Porta: $DB_PORT"
    echo "  Banco de dados: $DB_DATABASE"
    echo "  Usuário: $DB_USER"
    echo "  Senha: $DB_PASSWORD"
    echo ""
    echo "Comandos úteis:"
    echo "  Ver logs: docker logs $CONTAINER_NAME"
    echo "  Acessar o container: docker exec -it $CONTAINER_NAME mysql -u$DB_USER -p$DB_PASSWORD $DB_DATABASE"
    echo "  Acessar como root: docker exec -it $CONTAINER_NAME mysql -uroot -prootpass123"
    echo "  Parar container: docker stop $CONTAINER_NAME"
    echo "  Iniciar novamente: docker start $CONTAINER_NAME"
else
    error_exit "Falha ao iniciar o container MySQL."
fi