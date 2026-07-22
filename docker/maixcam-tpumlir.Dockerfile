ARG TPUC_DEV_IMAGE=sophgo/tpuc_dev:v3.4
FROM ${TPUC_DEV_IMAGE}

ARG TPU_MLIR_VERSION=1.28.1
RUN python3 -m pip install --no-cache-dir "tpu_mlir==${TPU_MLIR_VERSION}"
