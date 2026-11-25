$(document).ready(function () {
    const $search = $("#organizationSearch");
    const $results = $("#navOrganizationList");
    const $noResults = $("#organizationNoResults");

    if (!$search.length) return;

    const searchUrl = $results.data("search-url");
    const datasetLabel = $results.data("dataset-label");

    let searchTimeout;
    let currentRequest;

    function searchOrganizations() {
        const query = $search.val().trim();

        if (currentRequest) {
            currentRequest.abort();
        }

        currentRequest = $.ajax({
            url: searchUrl,
            data: { q: query },
            dataType: "json",

            success: function (data) {
                $results.empty();

                data.organizations.forEach(function (organization) {
                    const $item = $("<a>", {
                        href: organization.url,
                        class: "navbar-item is-flex is-justify-content-space-between is-align-items-center organization-result"
                    });

                    $("<span>", {
                        class: "pr-3"
                    }).text(organization.title).appendTo($item);

                    $("<span>", {
                        class: "has-text-grey is-size-7"
                    }).text(`${organization.dataset_count} ${datasetLabel}`)
                      .appendTo($item);

                    $results.append($item);
                });

                $noResults.prop("hidden", data.organizations.length > 0);
            },

            error: function (xhr, status) {
                console.error("Organization search failed:", status);
            }
        });
    }

    $search.on("input", function () {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(searchOrganizations, 300);
    });
});