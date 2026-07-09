# ──────────────────────────────────────────────────────────────────────────────
# Stage 1: Build
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy project files and install
COPY pyproject.toml ./
COPY harness/ ./harness/
RUN pip install --no-cache-dir --target=/install .

# ──────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /workspace

# Install runtime dependencies
RUN pip install --no-cache-dir --upgrade pip

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local/lib/python3.11/site-packages/

# Copy entry point modules
COPY harness/ /usr/local/lib/python3.11/site-packages/harness/

# Volume for credential persistence (SPEC §7.2.2)
VOLUME ["/root/.local/share/ai4se-harness"]

# Default config
COPY config.toml /etc/ai4se-harness/config.toml

ENTRYPOINT ["ai4se-harness"]
CMD ["--help"]