"""Export a demo lock's provisioning header locally; never expose its secret via HTTP."""
import argparse
import os
from pathlib import Path

import mysql.connector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("lock_id", type=int)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[2] / "flike-firmware/include/flike_config.local.h")
    args = parser.parse_args()
    if (os.getenv("DB_HOST"), os.getenv("DB_PORT"), os.getenv("DB_DATABASE")) != ("127.0.0.1", "55470", "flike_demo"):
        raise SystemExit("Provisionamento limitado ao banco local isolado de demonstração.")
    with mysql.connector.connect(host="127.0.0.1", port=55470, database="flike_demo", user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"]) as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("""SELECT l.id, l.secret_key FROM digital_lock l
                JOIN room r ON r.id=l.room_id JOIN building b ON b.id=r.building_id
                JOIN institution i ON i.id=b.institution_id JOIN user u ON u.id=i.owner_id
                WHERE l.id=%s AND u.email='responsavel@example.com'""", (args.lock_id,))
            lock = cursor.fetchone()
    if lock is None:
        raise SystemExit("Tranca não encontrada entre os recursos do responsável da demonstração.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise SystemExit("Configuração local já existe; preservada sem sobrescrita.") from None
    with os.fdopen(descriptor, "w") as stream:
        stream.write("#pragma once\n#include <cstdint>\n")
        stream.write(f"#define FLIKE_LOCK_ID UINT64_C({lock['id']})\n")
        stream.write(f"#define FLIKE_AES_KEY_HEX \"{bytes(lock['secret_key']).hex()}\"\n")
        stream.write("#define FLIKE_RELAY_PIN 13\n#define FLIKE_RELAY_ENABLED false\n")
    print(f"Configuração gravada em {args.output}. Relé permanece desabilitado até conferência física.")


if __name__ == "__main__":
    main()
