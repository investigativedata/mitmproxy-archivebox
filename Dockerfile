FROM mitmproxy/mitmproxy:latest

LABEL org.opencontainers.image.title="mitmproxy-archivebox"
LABEL org.opencontainers.image.licenses=MIT
LABEL org.opencontainers.image.source=https://github.com/investigativedata/mitmproxy-archivebox

COPY requirements.txt /home/mitmproxy/requirements_archivebox.txt
RUN pip install --no-cache-dir -r /home/mitmproxy/requirements_archivebox.txt
COPY archivebox.py /home/mitmproxy/archivebox.py

CMD ["mitmdump", "-s /home/mitmproxy/archivebox.py"]
