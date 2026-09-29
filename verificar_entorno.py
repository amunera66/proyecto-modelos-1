"""Verifica que el entorno de ML quedo bien instalado en Windows ARM64."""

import importlib
import platform
import struct
import sys

PAQUETES = [
    "pandas", "numpy", "sklearn", "scipy", "matplotlib",
    "seaborn", "jupyter_core", "ipykernel", "joblib", "pytest", "kaggle",
]


def seccion(titulo):
    print(f"\n{'=' * 62}\n{titulo}\n{'=' * 62}")


def main():
    seccion("1. INTERPRETE Y ARQUITECTURA")
    print(f"Python            : {sys.version.splitlines()[0]}")
    print(f"platform.machine(): {platform.machine()}")
    print(f"platform.system() : {platform.system()} {platform.release()}")
    print(f"processor         : {platform.processor()}")
    print(f"architecture()    : {platform.architecture()[0]}")
    print(f"puntero           : {struct.calcsize('P') * 8} bits")
    print(f"ejecutable        : {sys.executable}")
    print(f"en venv           : {sys.prefix != sys.base_prefix}")

    nativo = platform.machine().upper() in ("ARM64", "AARCH64")
    print(f"\n>>> {'ARM64 NATIVO (sin emulacion)' if nativo else 'x64 EMULADO'}")

    seccion("2. VERSIONES DE LAS LIBRERIAS")
    fallos = []
    for nombre in PAQUETES:
        try:
            mod = importlib.import_module(nombre)
            print(f"  {nombre:<14} {getattr(mod, '__version__', 'sin __version__')}")
        except Exception as exc:                      # noqa: BLE001
            print(f"  {nombre:<14} ERROR: {exc}")
            fallos.append(nombre)

    seccion("3. ENTRENAMIENTO DE PRUEBA (pandas + scikit-learn)")
    import pandas as pd
    from sklearn.datasets import load_iris
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score
    from sklearn.model_selection import train_test_split

    datos = load_iris(as_frame=True)
    df = datos.frame
    print(f"Dataset iris -> DataFrame {df.shape[0]} filas x {df.shape[1]} columnas")
    print(df.head(3).to_string(index=False))

    X = df.drop(columns="target")
    y = df["target"]
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    modelo = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    modelo.fit(X_tr, y_tr)
    acc = accuracy_score(y_te, modelo.predict(X_te))
    print(f"\nRandomForest entrenado -> accuracy = {acc:.4f} sobre {len(y_te)} muestras")

    seccion("4. joblib (guardar / cargar modelo)")
    import io

    import joblib

    buf = io.BytesIO()
    joblib.dump(modelo, buf)
    buf.seek(0)
    recargado = joblib.load(buf)
    print(f"round-trip OK -> misma prediccion: "
          f"{(recargado.predict(X_te) == modelo.predict(X_te)).all()}")

    seccion("5. matplotlib (backend headless)")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme()
    fig, ax = plt.subplots(figsize=(4, 3))
    sns.scatterplot(data=df, x=df.columns[0], y=df.columns[1], hue="target", ax=ax)
    fig.savefig("_verificacion_grafico.png", dpi=80, bbox_inches="tight")
    plt.close(fig)
    print("Grafico seaborn+matplotlib generado: _verificacion_grafico.png")

    seccion("RESULTADO")
    if fallos:
        print(f"FALLARON: {', '.join(fallos)}")
        return 1
    print("TODO CORRECTO: las 11 librerias importan y el modelo entrena.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
