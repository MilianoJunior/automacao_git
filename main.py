import os
import asyncio
import subprocess
import time
import logging
import sys

# Configurações
REPOS = {
    "/var/www/conversa-o": {
        "servicos": ["conversa-o.service", "nginx"],
        "cmd": "pip install -r requirements.txt"
    },
    "/var/www/leo": {
        "servicos": ["leo.service", "nginx"],
        "cmd": "npm install"
    },
    "/var/www/COG": {
        "servicos": ["COG.service", "nginx"],
        "cmd": "npm install"
    },
}
INTERVALO_CHECAGEM = 30  # Tempo em segundos

# Configuração do logging
logging.basicConfig(
    filename="/var/log/git_monitor.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

async def run_command(command, cwd=None):
    """Executa um comando de forma assíncrona e retorna True se sucesso, False se falha"""
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logging.error(f'Erro ao executar comando: {command}')
            logging.error(f'Erro: {stderr.decode()}')
            return False
            
        logging.info(f'Comando executado com sucesso: {command}')
        return True
        
    except Exception as e:
        logging.error(f'Exceção ao executar comando {command}: {str(e)}')
        return False

async def reiniciar_servicos(servicos):
    """Reinicia os serviços especificados de forma assíncrona."""
    for servico in servicos:
        logging.info(f"Reiniciando serviço: {servico}")
        await run_command(f"sudo systemctl restart {servico}")

async def verificar_repositorio(repo, config):
    """Verifica um repositório específico por mudanças."""
    logging.info(f"Verificando {repo}...")
    
    # Verifica se diretório existe
    if not os.path.exists(repo):
        logging.error(f"Diretório {repo} não existe!")
        return False
    
    # Atualiza informações do repositório
    if not await run_command("git fetch origin main", cwd=repo):
        return False
    
    # Verifica se há mudanças
    process = await asyncio.create_subprocess_shell(
        "git status -uno",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=repo
    )
    stdout, _ = await process.communicate()
    status = stdout.decode()
    
    if "Your branch is behind" in status:
        print("Mudança detectada em ",repo)
        logging.info(f"Mudança detectada em {repo}. Atualizando...")
        if not await run_command("git pull origin main", cwd=repo):
            return False
        if not await run_command(config["cmd"], cwd=repo):
            return False
        await reiniciar_servicos(config["servicos"])
    else:
        logging.info(f"Nenhuma mudança detectada em {repo}.")
        print("Nenhuma mudança detectada em ",repo)
        print(' ')
    
    return True

async def monitor_repos():
    """Monitora todos os repositórios continuamente."""
    while True:
        for repo, config in REPOS.items():
            await verificar_repositorio(repo, config)
        await asyncio.sleep(INTERVALO_CHECAGEM)

if __name__ == "__main__":
    try:
        logging.info("Iniciando monitoramento de repositórios...")
        asyncio.run(monitor_repos())
    except KeyboardInterrupt:
        logging.info("Monitoramento interrompido pelo usuário.")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Erro fatal: {str(e)}")
        sys.exit(1)
