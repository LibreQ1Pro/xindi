# Reference environment for the xindi E2E equivalence tests.
#
# The image is built for linux/arm64 (runs through qemu binfmt on x86 hosts) so
# that the original aarch64 helper binaries from the printer (/root/uart and
# /home/mks/libColPic.so used by gene4.py) can be executed unchanged next to the
# C++ build, which gives an authentic reference for the Python port.
FROM --platform=linux/arm64 debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake wget ca-certificates xz-utils \
        libboost-system-dev libwebsocketpp-dev \
        python3 python3-pil python3-numpy python3-aiohttp \
        socat procps psmisc \
    && rm -rf /var/lib/apt/lists/*

# libwpa_client (wpa_ctrl.c) from the hostap sources, as used by the C++ code.
# (wpa_2.10.orig.tar.xz is the upstream 2.10 release as shipped by Debian,
# downloaded by build_images.sh)
COPY wpa_2.10.orig.tar.xz /tmp/hostap/
RUN cd /tmp/hostap && tar xJf wpa_2.10.orig.tar.xz && cd wpa-2.10 \
    && gcc -O2 -c -DCONFIG_CTRL_IFACE -DCONFIG_CTRL_IFACE_UNIX -Isrc -Isrc/utils src/common/wpa_ctrl.c -o wpa_ctrl.o \
    && gcc -O2 -c -Isrc -Isrc/utils src/utils/os_unix.c -o os_unix.o \
    && ar rcs /usr/local/lib/libwpa_client.a wpa_ctrl.o os_unix.o \
    && cp src/common/wpa_ctrl.h /usr/local/include/ \
    && rm -rf /tmp/hostap

# C++ sources of xindi (copied into the build context by build_images.sh)
COPY cpp/ /opt/xindi_cpp/
RUN mkdir -p /opt/xindi_cpp/include/nlohmann \
    && cp /opt/xindi_cpp/include/json.hpp /opt/xindi_cpp/include/nlohmann/json.hpp \
    && mkdir -p /opt/xindi_cpp/build && cd /opt/xindi_cpp/build \
    && cmake -DCMAKE_BUILD_TYPE= -DCMAKE_CXX_FLAGS="-I/opt/xindi_cpp/include -w -fpermissive" .. \
    && make -j"$(nproc)" xindi

# Original helper binaries / scripts from the printer eMMC
COPY printer/uart /root/uart
COPY printer/gene4.py /home/mks/gene4.py
COPY printer/libColPic.so /home/mks/libColPic.so
RUN chmod +x /root/uart

# Test harness support: logging /bin/sh wrapper, stub commands, sleep scaler
COPY support/ /opt/support/
RUN gcc -O2 -shared -fPIC /opt/support/timescale.c -o /opt/support/timescale.so -ldl \
    && sh /opt/support/install.sh
