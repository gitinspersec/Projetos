<!-- ©AngelaMos | 2026 -->
<!-- DEMO.md -->

<div align="center">

```ruby
██████╗  ██████╗ ██████╗ ████████╗    ███████╗ ██████╗ █████╗ ███╗   ██╗███╗   ██╗███████╗██████╗
██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝    ██╔════╝██╔════╝██╔══██╗████╗  ██║████╗  ██║██╔════╝██╔══██╗
██████╔╝██║   ██║██████╔╝   ██║       ███████╗██║     ███████║██╔██╗ ██║██╔██╗ ██║█████╗  ██████╔╝
██╔═══╝ ██║   ██║██╔══██╗   ██║       ╚════██║██║     ██╔══██║██║╚██╗██║██║╚██╗██║██╔══╝  ██╔══██╗
██║     ╚██████╔╝██║  ██║   ██║       ███████║╚██████╗██║  ██║██║ ╚████║██║ ╚████║███████╗██║  ██║
╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝       ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝
```

**Demonstração e Prévia**

<br>

<a href="https://github.com/CarterPerez-dev/Cybersecurity-Projects/tree/main/PROJECTS/beginner/simple-port-scanner">
  <img src="https://img.shields.io/badge/C++20-Boost.Asio-00599C?style=for-the-badge&logo=cplusplus&logoColor=white" alt="C++ Boost.Asio"/>
</a>

<br>

```ruby
mkdir build && cd build && cmake .. && make
./simplePortScanner -i <target> -p <range>
```

<br>

[Descoberta de SSH](#ssh-discovery) · [Descoberta de HTTP](#http-discovery)

</div>

---

### Descoberta de SSH

Scan TCP assíncrono contra scanme.nmap.org com mapeamento de serviço detalhado mostrando estados OPEN/CLOSED/FILTERED em todo o intervalo de portas conhecidas de SSH

![Descoberta de SSH](assets/scan-low.png)

---

### Descoberta de HTTP

Scan concorrente em toda a janela de portas HTTP com identificação de serviço por porta e contagem de resultados agregados

![Descoberta de HTTP](assets/scan-http.png)
