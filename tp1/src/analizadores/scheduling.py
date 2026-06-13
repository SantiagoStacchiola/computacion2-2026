# src/analizadores/scheduling.py

from procfs import extraer_cambios_de_contexto


POLICY_MAP = {
    0: "OTHER",
    1: "FIFO",
    2: "RR",
    3: "BATCH",
    5: "IDLE",
    6: "DEADLINE",
}


def traducir_policy(policy_num):
    return POLICY_MAP.get(policy_num, f"UNKNOWN({policy_num})")


def construir_scheduling(snapshot, snapshot_anterior=None):
    procesos_scheduling = []

    for pid, datos in snapshot["procesos"].items():
        stat = datos["stat"]
        status = datos["status"]

        ctx = extraer_cambios_de_contexto(status)

        proceso_scheduling = {
            "pid": pid,
            "nombre": stat["comm"],
            "nice": stat.get("nice", 0),
            "priority": stat.get("priority", 0),
            "policy_num": stat.get("policy", -1),
            "policy": traducir_policy(stat.get("policy", -1)),
            "rt_priority": stat.get("rt_priority", 0),
            "pgid": stat.get("pgid", 0),
            "sid": stat.get("sid", 0),
            "cpu_affinity": status.get("Cpus_allowed_list", ""),
            "voluntary_ctxt_switches": ctx["voluntary_ctxt_switches"],
            "nonvoluntary_ctxt_switches": ctx["nonvoluntary_ctxt_switches"],
            "utime": stat["utime"],
            "stime": stat["stime"],
        }

        procesos_scheduling.append(proceso_scheduling)

    procesos_scheduling.sort(key=lambda p: p["pid"])
    return procesos_scheduling