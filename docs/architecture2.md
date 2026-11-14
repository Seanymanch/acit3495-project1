# Architecture and design decisions

![Cloud Kubernetes architecture](architecture.png)

Source is `architecture.dot` and editable using Graphviz (`dot -Tpng docs/architecture.dot -o docs/architecture.png`).

The **real Project 1 temperature analytics app** is deployed into an EKS namespace, not replaced by a synthetic HPA demonstration app. It includes four application containers and two databases. Internal API and database services stay ClusterIP / headless. A user reaches the two web frontends via authenticated Kubernetes `port-forward`, or via the optional demo-only external LoadBalancer Services.

**Authentication backend is the selected scaling target.** Each real login uses PBKDF2 password verification, a CPU-demanding task. K6 repeats the full flow to create load on the auth deployment while continuing to test the database write and analytics refresh. The autoscaler reads CPU metrics from EKS Metrics Server and changes auth Deployment replicas from 1 to at most 5 at a target average CPU utilization of 60% of each pod's requested 100m CPU. Scale-down uses a 120-second stabilization window. EKS worker nodes are fixed at three in this exercise, so pod autoscaling does not imply node autoscaling.

MySQL and MongoDB each have a single StatefulSet replica with an encrypted EBS gp3 PersistentVolumeClaim. EBS is ReadWriteOnce and AZ-scoped, so database pods aren't horizontally scaled. App configuration uses ConfigMaps, non-committed Secret data and environment variables. Readiness probes check dependent stores; liveness probes check the process. The public optional services are plain HTTP and **not appropriate for real personal credentials or production**. Use only the generated demo user and remove them after demonstration; TLS is a future improvement.
