/**
 * Stored Checkbox State preserves checkbox state between webpage reloads.
 *
 * If you decorate a container with class="stored-checkbox-state" then any checkboxes
 * within it will have their state preserved in local storage between launches.
 */
 
const storedCheckboxStateBootstrap = () => {

const onChange = event => {
    const id = event.target.id
    if (!id) return
    window.localStorage.setItem('cached-' + id, event.target.checked)
}

const wireUpElements = () => {
    const containers = document.getElementsByClassName('stored-checkbox-state')
    for (container of containers) {
        const inputs = Array.from(container.getElementsByTagName('input'))
        const checkboxes = inputs.filter(e => e.getAttribute('type') == 'checkbox' && !!e.getAttribute('id'))
        for (input of checkboxes) {
            input.addEventListener('change', onChange)
            const id = input.getAttribute('id')
            const state = window.localStorage.getItem('cached-' + id)
            const checked = state == 'true'
            if (state && checked != input.checked) {
                input.checked = checked
                const event = new Event('change')
                event.target = input
                input.dispatchEvent(event)
            }
        }
    }
}

window.addEventListener('load', wireUpElements)

}

storedCheckboxStateBootstrap()
