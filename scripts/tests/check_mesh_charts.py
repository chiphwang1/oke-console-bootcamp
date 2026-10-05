"""Render-only contract checks. No kubeconfig, cluster calls, or live credentials."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LOCAL_ONLY = "--local-only" in sys.argv
if LOCAL_ONLY:
    sys.argv.remove("--local-only")


def render(release, chart, namespace="oke-lab", extra=()):
    result = subprocess.run(
        ["helm", "template", release, chart, "--namespace", namespace,
         "--kube-version", "1.36.1", *extra],
        cwd=ROOT, text=True, capture_output=True, check=True, timeout=120,
    )
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def resource(docs, kind, name):
    return next(doc for doc in docs if doc["kind"] == kind
                and doc["metadata"]["name"] == name)


class AppCharts(unittest.TestCase):
    def test_grafana_dashboard_queries_match_existing_mesh_metrics(self):
        dashboard = json.loads((ROOT / "helm/dashboards/oke-lab.json").read_text())
        self.assertEqual(dashboard["uid"], "oke-lab")
        self.assertFalse(dashboard["editable"])
        self.assertEqual(dashboard["refresh"], "15s")
        self.assertIn(dashboard["refresh"], dashboard["timepicker"]["refresh_intervals"])
        panels = [p for p in dashboard["panels"] if p["type"] != "text"]
        self.assertEqual(len(panels), 8)
        for panel in panels:
            self.assertEqual(panel["datasource"]["uid"], "oke-prometheus")
            for target in panel["targets"]:
                self.assertNotIn("kube_horizontalpodautoscaler", target["expr"])
        count_panel = next(p for p in panels if p["title"] == "Application proxies up")
        self.assertIn('pod=~"hello-oke-[a-f0-9]+-.*"', count_panel["targets"][0]["expr"])
        self.assertIn("not HPA", dashboard["description"])

    def test_summary_cards_do_not_reduce_historical_values(self):
        dashboard = json.loads((ROOT / "helm/dashboards/oke-lab.json").read_text())
        stats = [p for p in dashboard["panels"] if p["type"] == "stat"]
        self.assertEqual(len(stats), 4)
        for panel in stats:
            with self.subTest(panel=panel["title"]):
                self.assertEqual(panel["options"]["reduceOptions"]["calcs"], ["last"])
                self.assertEqual(panel["options"]["graphMode"], "none")
                defaults = panel["fieldConfig"]["defaults"]
                self.assertEqual(defaults["noValue"], "No data")
                self.assertIn({"type": "special", "options": {
                    "match": "nan", "result": {"text": "No data"}}}, defaults["mappings"])
                for target in panel["targets"]:
                    self.assertTrue(target["instant"])
                    self.assertFalse(target["range"])
                    self.assertNotIn("or vector(0)", target["expr"])
        graphs = [p for p in dashboard["panels"] if p["type"] == "timeseries"]
        self.assertEqual(len(graphs), 4)
        for panel in graphs:
            for target in panel["targets"]:
                self.assertTrue(target["range"])
                self.assertFalse(target.get("instant", False))
        scaling = next(p for p in graphs if p["id"] == 7)
        self.assertIn("not a required peak", scaling["description"])

    def test_default_app_and_service_match(self):
        docs = render("hello-oke", "./charts/oke-mesh-app")
        self.assertEqual(len(docs), 3)
        app = resource(docs, "Deployment", "hello-oke")["spec"]
        service = resource(docs, "Service", "hello-oke")["spec"]
        self.assertEqual(app["replicas"], 2)
        self.assertEqual(service["type"], "LoadBalancer")
        for key, value in service["selector"].items():
            self.assertEqual(app["template"]["metadata"]["labels"][key], value)
        self.assertEqual(service["ports"][0]["appProtocol"], "http")
        self.assertEqual(app["template"]["metadata"]["labels"]["version"], "v1")
        web = app["template"]["spec"]["containers"][0]
        self.assertEqual(web["resources"]["requests"]["cpu"], "100m")
        self.assertEqual(web["readinessProbe"]["httpGet"]["path"], "/healthz")
        self.assertTrue(web["securityContext"]["readOnlyRootFilesystem"])
        server = resource(docs, "ConfigMap", "hello-oke-server")["data"]["server.py"]
        self.assertEqual(server.strip(), (ROOT / "charts/oke-mesh-app/files/server.py").read_text().strip())

    def test_traffic_is_opt_in_and_targets_release(self):
        docs = render("example", "./charts/oke-mesh-app", extra=("--set", "traffic.enabled=true"))
        self.assertEqual(len(docs), 4)
        traffic = resource(docs, "Deployment", "example-traffic")
        container = traffic["spec"]["template"]["spec"]["containers"][0]
        self.assertIn("http://example:80/", container["args"][0])
        self.assertIn("sleep 2", container["args"][0])
        self.assertTrue(container["securityContext"]["runAsNonRoot"])
        self.assertNotIn("/work", container["args"][0])

    def test_hpa_owns_replicas_and_targets_web_not_proxy(self):
        docs = render("example", "./charts/oke-mesh-app", extra=(
            "-f", "helm/values/student.yaml", "--set", "autoscaling.enabled=true"))
        self.assertNotIn("replicas", resource(docs, "Deployment", "example")["spec"])
        hpa = resource(docs, "HorizontalPodAutoscaler", "example")["spec"]
        self.assertEqual(hpa["scaleTargetRef"]["name"], "example")
        self.assertEqual((hpa["minReplicas"], hpa["maxReplicas"]), (2, 6))
        self.assertEqual(hpa["metrics"], [{"type": "ContainerResource", "containerResource": {
            "name": "cpu", "container": "web",
            "target": {"type": "Utilization", "averageUtilization": 60}}}])
        self.assertEqual(hpa["behavior"]["scaleDown"]["stabilizationWindowSeconds"], 60)

    def test_load_is_bounded_and_returns_to_baseline(self):
        docs = render("example", "./charts/oke-mesh-app", extra=(
            "--set", "traffic.enabled=true,traffic.loadEnabled=true,autoscaling.enabled=true"))
        traffic = resource(docs, "Deployment", "example-traffic")
        script = traffic["spec"]["template"]["spec"]["containers"][0]["args"][0]
        self.assertIn("+ 300", script)
        self.assertIn('"$worker" -lt 2', script)
        self.assertIn('"$(date +%s)" -lt "$deadline"', script)
        self.assertIn("http://example:80/work", script)
        self.assertIn("CPU load finished; returning to baseline traffic.", script)
        self.assertIn("sleep 2", script)
        subprocess.run(["sh", "-n"], input=script, text=True, check=True)

    def test_rejects_unbounded_load_and_invalid_hpa_range(self):
        for value in ("traffic.durationSeconds=3600", "traffic.concurrency=100",
                      "autoscaling.enabled=true,autoscaling.minReplicas=6,autoscaling.maxReplicas=2"):
            with self.subTest(value=value), self.assertRaises(subprocess.CalledProcessError):
                render("example", "./charts/oke-mesh-app", extra=("--set", value))

    def test_student_customization_and_manual_scaling(self):
        docs = render("hello-oke", "./charts/oke-mesh-app", extra=(
            "-f", "helm/values/student.yaml", "--set", "replicaCount=4"))
        app = resource(docs, "Deployment", "hello-oke")["spec"]
        self.assertEqual(app["replicas"], 4)
        student_values = yaml.safe_load((ROOT / "helm/values/student.yaml").read_text())
        web = app["template"]["spec"]["containers"][0]
        env = {item["name"]: item.get("value") for item in web["env"]}
        self.assertEqual(env["APP_MESSAGE"], student_values["message"])
        self.assertFalse(any(d["kind"] == "HorizontalPodAutoscaler" for d in docs))

    def test_custom_message_override_does_not_require_editing_student_file(self):
        message = "Hello from a learner's chart test"
        docs = render("hello-oke", "./charts/oke-mesh-app", extra=(
            "-f", "helm/values/student.yaml", "--set-string", f"message={message}"))
        web = resource(docs, "Deployment", "hello-oke")["spec"]["template"]["spec"]["containers"][0]
        env = {item["name"]: item.get("value") for item in web["env"]}
        self.assertEqual(env["APP_MESSAGE"], message)


@unittest.skipIf(LOCAL_ONLY, "Upstream chart rendering explicitly skipped (--local-only)")
class UpstreamCharts(unittest.TestCase):
    def test_grafana_is_internal_provisioned_and_has_no_cluster_permissions(self):
        docs = render("grafana", "grafana", "istio-system", (
            "--repo", "https://grafana-community.github.io/helm-charts",
            "--version", os.environ["GRAFANA_CHART_VERSION"],
            "-f", "helm/values/grafana.yaml",
            "--set-file", "dashboards.default.oke-lab.json=helm/dashboards/oke-lab.json"))
        self.assertFalse(any(d["kind"] in ("PersistentVolumeClaim", "Ingress", "ClusterRole", "ClusterRoleBinding", "Role", "RoleBinding") for d in docs))
        self.assertEqual(resource(docs, "Service", "grafana")["spec"]["type"], "ClusterIP")
        pod = resource(docs, "Deployment", "grafana")["spec"]["template"]["spec"]
        self.assertFalse(pod["automountServiceAccountToken"])
        grafana = next(c for c in pod["containers"] if c["name"] == "grafana")
        self.assertEqual(grafana["resources"]["requests"]["memory"], "512Mi")
        self.assertEqual(grafana["resources"]["limits"]["memory"], "1Gi")
        memory_targets = [e["value"] for e in grafana["env"] if e["name"] == "GOMEMLIMIT"]
        self.assertEqual(memory_targets, ["512MiB"])
        config = resource(docs, "ConfigMap", "grafana")["data"]
        sources = yaml.safe_load(config["datasources.yaml"])["datasources"]
        self.assertEqual(sources[0]["uid"], "oke-prometheus")
        self.assertEqual(sources[0]["url"], "http://prometheus-server.istio-system.svc.cluster.local:80")
        self.assertFalse(sources[0]["editable"])
        self.assertIn("org_role = Viewer", config["grafana.ini"])
        dashboards = [json.loads(value) for doc in docs if doc["kind"] == "ConfigMap"
                      for key, value in doc.get("data", {}).items() if key == "oke-lab.json"]
        self.assertEqual(len(dashboards), 1)
        self.assertEqual(dashboards[0]["uid"], "oke-lab")

    def test_istio_base_and_control_plane(self):
        repo = "https://blob.istio.io/istio-release/charts"
        version = os.environ["ISTIO_VERSION"]
        base = render("istio-base", "base", "istio-system",
                      ("--repo", repo, "--version", version, "--include-crds",
                       "--set", "defaultRevision=default"))
        self.assertTrue(any(d["kind"] == "CustomResourceDefinition" for d in base))
        docs = render("istiod", "istiod", "istio-system",
                      ("--repo", repo, "--version", version, "-f", "helm/values/istiod.yaml"))
        deploy = resource(docs, "Deployment", "istiod")
        self.assertEqual(deploy["spec"]["replicas"], 1)
        self.assertEqual(deploy["spec"]["template"]["spec"]["containers"][0]
                         ["resources"]["requests"]["memory"], "256Mi")
        self.assertFalse(any(d["kind"] == "HorizontalPodAutoscaler" for d in docs))
        mesh = yaml.safe_load(resource(docs, "ConfigMap", "istio")["data"]["mesh"])
        self.assertTrue(mesh["defaultConfig"]["holdApplicationUntilProxyStarts"])

    def test_prometheus_is_ephemeral_and_scrapes_mesh(self):
        docs = render("prometheus", "prometheus", "istio-system", (
            "--repo", "https://prometheus-community.github.io/helm-charts",
            "--version", os.environ["PROMETHEUS_CHART_VERSION"],
            "-f", "helm/values/prometheus.yaml"))
        self.assertFalse(any(d["kind"] in ("PersistentVolumeClaim", "Ingress", "DaemonSet") for d in docs))
        service = resource(docs, "Service", "prometheus-server")
        self.assertEqual(service["spec"]["type"], "ClusterIP")
        self.assertEqual(service["spec"]["ports"][0]["port"], 80)
        config = yaml.safe_load(resource(docs, "ConfigMap", "prometheus-server")["data"]["prometheus.yml"])
        jobs = {job["job_name"]: job for job in config["scrape_configs"]}
        self.assertEqual(set(jobs), {"istiod", "istio-workloads"})
        self.assertEqual(jobs["istio-workloads"]["relabel_configs"][0]["regex"], "http-envoy-prom")
        self.assertEqual(jobs["istio-workloads"]["kubernetes_sd_configs"][0]["namespaces"]["names"], ["oke-lab"])

    def test_kiali_is_internal_readonly_and_wired_to_prometheus(self):
        docs = render("kiali-server", "kiali-server", "istio-system", (
            "--repo", "https://kiali.org/helm-charts",
            "--version", os.environ["KIALI_CHART_VERSION"],
            "-f", "helm/values/kiali.yaml"))
        self.assertFalse(any(d["kind"] == "Ingress" for d in docs))
        self.assertEqual(resource(docs, "Service", "kiali")["spec"]["type"], "ClusterIP")
        config = yaml.safe_load(resource(docs, "ConfigMap", "kiali")["data"]["config.yaml"])
        self.assertEqual(config["auth"]["strategy"], "anonymous")
        self.assertTrue(config["deployment"]["view_only_mode"])
        self.assertEqual(config["external_services"]["prometheus"]["url"],
                         "http://prometheus-server.istio-system.svc.cluster.local:80")
        self.assertEqual(config["server"]["web_root"], "/kiali")
        for doc in docs:
            if doc["kind"] in ("ClusterRole", "Role"):
                for rule in doc.get("rules", []):
                    # Upstream viewer role uses API subresources for inspection/auth.
                    if rule.get("resources") in (["pods/portforward"], ["tokenreviews"]):
                        self.assertEqual(rule["verbs"], ["create"])
                        continue
                    self.assertFalse({"create", "update", "patch", "delete", "*"} & set(rule["verbs"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
