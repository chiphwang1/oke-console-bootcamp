# Access your OKE cluster

Use this page for additional kubeconfig instructions or access troubleshooting during hands-on [step 1](../README.md#1-create-your-cluster-and-confirm-your-connection--4070-minutes). First complete [cluster creation](create-cluster.md) in your allocated compartment. Ask the instructor for help if access is blocked.

## Start with your Luna session

Follow [Find your lab login and compartment](../README.md#find-your-lab-login-and-compartment): open the **Luna-Lab** desktop icon (also labeled **Luna Lab**), choose **Quick Links → OCI Console**, and sign in with your assigned username and password from **Credentials**. Do not use the SSO Link. Paste with **Ctrl+V** or right-click **Paste**, then click **Sign In**. Find your assigned region and **Compartment Name** in **Lab Details** or the page's **Oracle Cloud** section. Missing login/session details require instructor help, not a new personal account.

In the Console, select the session's region. Open the navigation menu, then **Developer Services → Containers & Artifacts → Kubernetes Clusters (OKE)**. In the **Compartment** filter, expand the hierarchy if needed and select the exact compartment shown on your Luna Lab page. Open the cluster you created in the Console; wait until its status is Active. Select **Access Cluster** (under **Actions** if necessary), then **Local Access**, and copy the displayed command's cluster OCID and region into the example below. Run it in the **Luna desktop's Bash terminal**. Console login does not authenticate this terminal; its OCI CLI identity must already be configured. See [Oracle's cluster access guide](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengdownloadkubeconfigfile.htm).

## Generate your kubeconfig on the desktop

Use the cluster OCID and region from your cluster's Console access command. An OCID is OCI's resource identifier. Use the desktop OCI profile configured for your Luna session in `~/.oci/config`; ask for help if you cannot identify it. Use `DEFAULT` only if that is your session's profile. Do not generate new API keys for this exercise.

Replace the three placeholders below before running. This example uses the lab's API-key authentication and the public Kubernetes endpoint selected in the cluster creation exercise. The Luna desktop needs outbound TCP 6443 access to that endpoint. For an existing private-only cluster, use `PRIVATE_ENDPOINT` and its configured private network path; generating a kubeconfig does not change the cluster's endpoint.

```bash
export LAB_REGION='<your-session-region>'
export LAB_CLUSTER_OCID='<your-cluster-ocid>'
export LAB_OCI_PROFILE='<your-session-profile>'
unset KUBECONFIG
umask 077
mkdir -p "$HOME/.kube"
oci ce cluster create-kubeconfig --cluster-id "$LAB_CLUSTER_OCID" \
  --region "$LAB_REGION" --file "$HOME/.kube/config" \
  --token-version 2.0.0 --kube-endpoint PUBLIC_ENDPOINT \
  --profile "$LAB_OCI_PROFILE" --auth api_key --with-auth-context &&
chmod 600 "$HOME/.kube/config"
```

This writes connection settings for an existing cluster. `--file` selects the destination, and `--with-auth-context` preserves the selected profile and authentication mode for later token generation. If the file already contains contexts, Oracle's command merges the cluster details and selects the added context. Do not add `--overwrite`. See [Oracle's kubeconfig command reference](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/ce/cluster/create-kubeconfig.html) and [cluster access guide](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengdownloadkubeconfigfile.htm).

If your instructor supplies a different OCI config-file location, use that `OCI_CLI_CONFIG_FILE` setting in **every** new terminal. `--with-auth-context` preserves profile/auth choices, not a custom config-file location. Keep OCI CLI installed and credentials available: the kubeconfig invokes `oci ce cluster generate-token` automatically when Kubernetes tools need authentication. You do not run or copy that token yourself.

## Alternative: browser download through Cloud Shell

Skip this if you generated the file on the desktop above. In the assigned cluster's **Access cluster** dialog, select **Cloud Shell Access → Launch Cloud Shell**. Cloud Shell is a separate machine with its own pre-authenticated OCI CLI.

Run `umask 077`, then run the Console's `create-kubeconfig` command in Cloud Shell with its assigned OCID/region/endpoint, changing only `--file` to `"$HOME/oke-lab-kubeconfig"`. Use a new filename if it already exists. Do not add the desktop's API-key/profile flags or `--with-auth-context`: Cloud Shell authentication settings must not be embedded for desktop use.

Open the Cloud Shell menu at the top left, choose **Download**, enter `oke-lab-kubeconfig`, and click **Download**. Use the browser inside the Luna desktop so the download lands there. Then, in a **desktop terminal**:

```bash
mkdir -p "$HOME/.kube"
cp -i "$HOME/Downloads/oke-lab-kubeconfig" "$HOME/.kube/config"
chmod 600 "$HOME/.kube/config"
unset KUBECONFIG
export OCI_CLI_PROFILE='<your-session-profile>'
export OCI_CLI_AUTH=api_key
```

Adjust the source path if the browser used another download directory. If prompted to overwrite a file, answer **no** and ask the instructor which file to retain. File transfers do not preserve permissions. Set the profile/auth variables in **every new desktop terminal** for this alternative, plus the instructor's `OCI_CLI_CONFIG_FILE` if needed. These use the lab's existing desktop credentials; never copy Cloud Shell's `/etc/oci` credentials. See [Oracle's Cloud Shell download and authentication instructions](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/devcloudshellgettingstarted.htm).

A downloaded kubeconfig does not establish network access or grant permissions. A private endpoint requires a platform-provided private network path; even a public endpoint may restrict source addresses. Do not change endpoint/firewall settings or create credentials to bypass a connection failure.

## Verify the selected file and context

kubectl and Helm use `~/.kube/config` by default; the current context selects an entry inside it. Changing directories does not select a cluster. In each new terminal, clear any inherited `KUBECONFIG` override so all lab commands use the default file:

```bash
unset KUBECONFIG
ls -l "$HOME/.kube/config" &&
test -s "$HOME/.kube/config" &&
kubectl config get-contexts &&
kubectl config current-context
```

If older instructions set `KUBECONFIG` to `~/.kube/oke-lab`, use `unset KUBECONFIG` above instead. If the default file is missing or empty, [generate it](#generate-your-kubeconfig-on-the-desktop) before continuing; changing the environment variable does not create a kubeconfig.

The kubeconfig command selects your cluster's context. If the file contains only that context, no selection command is needed. If you use a file with multiple contexts and need to switch back to your Luna cluster, copy its context name from the list:

```bash
kubectl config use-context '<your-cluster-context-name-from-the-list>'
```

This saves the selection in the kubeconfig. New terminals using that file share the saved context; repeat `use-context` only when you need to switch it. `kubectl config current-context` and the lab preflight check the selection without changing it.

If your cluster's context is absent, confirm the file path or generate the kubeconfig above. `no context exists` refers to the selected file; the same context may exist in another kubeconfig. Return to the README's read-only preflight check, which uses the current context without a `--context` argument.

## Optional extension: discover the cluster with OCI CLI

This is an optional addition to the core workflow. The main walkthrough obtains the assigned cluster OCID through the Console, so students can skip CLI discovery. For a separate OCI discovery exercise, obtain the session's compartment OCID, region, and profile, then list all pages:

```bash
export LAB_REGION='<your-session-region>'
export LAB_OCI_PROFILE='<your-session-profile>'
export LAB_COMPARTMENT_OCID='<your-session-compartment-ocid>'
oci ce cluster list --compartment-id "$LAB_COMPARTMENT_OCID" \
  --region "$LAB_REGION" --profile "$LAB_OCI_PROFILE" --auth api_key --all \
  --query 'data[].{Name:name,State:"lifecycle-state",OCID:id}' --output table
```

Find the cluster you created in your session's compartment and confirm `ACTIVE`. If the result is missing or ambiguous, ask for help. Oracle documents pagination and filters in the [cluster list reference](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/ce/cluster/list.html).

## Instructor access checks

Verify OCI CLI, kubectl, Helm, Git, and curl in the same Bash terminal learners use. The session's OCI profile must remain available for token generation in each terminal. Check full Helm permissions during rehearsal, including:

```bash
kubectl auth can-i create customresourcedefinitions.apiextensions.k8s.io
kubectl auth can-i create clusterroles.rbac.authorization.k8s.io
```

Both should return `yes`. These checks do not grant permissions and do not cover every action needed by the charts. A successful GitLab allocation check does not prove desktop authentication, cluster creation permissions, node capacity, or Helm installation. Follow the [instructor guide](instructor-guide.md).
