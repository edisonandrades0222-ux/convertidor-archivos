FROM python:3.11-slim

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema y herramientas de compilaci?n para LibreDWG
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    autoconf \
    libtool \
    texinfo \
    pkg-config \
    git \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Compilar e instalar LibreDWG para soporte 100% nativo de DWG en Linux
RUN git clone --depth 1 https://github.com/LibreDWG/libredwg.git /tmp/libredwg && \
    cd /tmp/libredwg && \
    sh autogen.sh && \
    ./configure --disable-shared --enable-static && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    rm -rf /tmp/libredwg

# Configurar directorio de trabajo
WORKDIR /app

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el c?digo fuente
COPY . .

# Puerto est?ndar para Hugging Face Spaces / Render / Cloud
EXPOSE 7860

# Comando de inicio del servidor web
CMD ["streamlit", "run", "web_app.py", "--server.port=7860", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
