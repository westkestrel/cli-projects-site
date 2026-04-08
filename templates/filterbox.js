/**
 * Filterbox allows you to use checkboxes to show and hide rows of data.
 *
 * To use it, you have a controls block. Note that if you omit the id=""
 * and for="" tags on the input and label, they will be inferred from the
 * label contents.  In the code below
 * - the first checkbox toggles "cats" (despite the label being "Felines")
 * - the second toggles "dogs" (inferred from the label)
 * - the third toggles "bugs", and ignores the explanatory text after the colon
 * - the fourth toggles "bugs", and ignores the explanatory text in parenthesis
 * - the fifth toggles "birds-and-bees" (spaces become hyphens)
 * - the sixth toggles both "birds" and "Bees" (commas separate items)
 *
 * <ul class="filterbox-controls filter-animals">
 * <li><input type="checkbox" id="cats"><label for="cats">Felines</label></li>
 * <li><input type="checkbox"><label>Dogs</label></li>
 * <li><input type="checkbox"><label>Bugs: six-legged beasties</label></li>
 * <li><input type="checkbox"><label>Bugs (six-legged beasties)</label></li>
 * <li><input type="checkbox"><label>Birds and Bees</label></li>
 * <li><input type="checkbox"><label>Birds, Bees</label></li>
 * </ul>
 *
 * and a data block:
 *
 * <table class="filterbox-data filter-animals">
 * <th>...</th>
 * <tr class="cats">...</tr>
 * <tr class="cats">...</tr>
 * <tr class="dogs">...</tr>
 * <tr class="birds">...</tr>
 * <tr class="bees">...</tr>
 * <tr class="birds-and-bees">...</tr>
 * </table>
 *
 * When the user toggles the checkbox for a given id, all data elements with that
 * class have their visibility toggled. In the case above if the user toggles
 * the last checkbox both the "birds" and "bees" rows will be hidden, but not the
 * "birds-and-bees" row.
 */
 
const filterboxBootstrap = () => {

const setVisibility = (filterType, filterClassName, flag) => {
    const targetClassName = `filterbox-data ${filterType}`
    const filterContainers = document.getElementsByClassName(targetClassName)
    if (!filterContainers.length) {
        console.error(`no element with class="${targetClassName}"`)
        return
    }
    for (container of filterContainers) {
        for (filterValue of filterClassName.split(' ')) {
            const className = container.getAttribute('class') || ''
            const hiddenPart = `hide-${filterValue}`
            const parts = className.split(' ').filter(x => x != hiddenPart)
            if (!flag) {
                parts.push(hiddenPart)
            }
            container.setAttribute('class', parts.join(' '))
        }
    }
}

const wireUpCheckboxes = () => {
    const cssRules = []
    const filters = document.getElementsByClassName('filterbox-controls')
    var metaKey = false
    const captureMetaKey = event => { metaKey = event.metaKey }
    for (filter of filters) {
        const filterType = filter.getAttribute('class').split(' ').filter(x => x.startsWith('filter-'))[0]
        if (!filterType) {
            console.error('filterbox-controls lacks a filter-TYPE class:', filter)
            continue
        }
        const toggles = filter.getElementsByTagName('input')
        for (toggle of toggles) {
            const toggleId = toggle.getAttribute('id')
            const label = toggle.nextElementSibling
            const filterValues = toggleId
                ? [toggleId]
                : label.innerHTML
                    .replace(/<span class="text">(.*?)<\/span>\s*/m, '$1')
                    .replace(/<span class="icon">(.*?)<\/span>\s*/m, '')
                    .toLocaleLowerCase()
                    .replace(/ *[(].*[)]/, '')
                    .replace(/:.*/, '')
                    .split(/, */)
                    .map(x => x.replace(/\W+/, ' ').trim().replace(' ', '-'))
            const filterId = `${filterType}-${filterValues.join('-')}`
            const filterClassName = filterValues.join(' ')
            if (!toggleId) { toggle.setAttribute('id', filterId) }
            if (!toggle.getAttribute('class')) { toggle.setAttribute('class', filterClassName) }
            label.setAttribute('for', toggleId || filterId)
            toggle.addEventListener('mousedown', captureMetaKey)
            toggle.addEventListener('mouseup', captureMetaKey)
            label.addEventListener('mousedown', captureMetaKey)
            label.addEventListener('mouseup', captureMetaKey)
            toggle.addEventListener('change', event => {
                if (metaKey) {
                    const wasChecked = event.target.checked
                    var allOthersWereChecked = true
                    for (t of toggles) {
                        if (t.getAttribute('id') != event.target.getAttribute('id')) {
                            allOthersWereChecked = allOthersWereChecked && t.checked
                        }
                    }
                    for (t of toggles) {
                        if (t.getAttribute('id') != event.target.getAttribute('id')) {
                            t.checked = !allOthersWereChecked
                            setVisibility(filterType, t.getAttribute('class'), !allOthersWereChecked)
                        } else {
                            t.checked = !wasChecked
                            setVisibility(filterType, filterClassName, t.checked)
                        }
                    }
                } else {
                    setVisibility(filterType, filterClassName, event.target.checked)
                }
            })
            toggle.checked = true
            for (filterValue of filterValues) {
                cssRules.push(`.filterbox-data.${filterType}.hide-${filterValue} .${filterValue} { display: none }`)
            }
        }
    }
    const head = document.getElementsByTagName('head')[0]
    const style = document.createElement('style')
    style.setAttribute('type', 'text/css')
    style.innerHTML = cssRules.join('\n')
    head.appendChild(style)
}

window.addEventListener('load', wireUpCheckboxes)
 
}
filterboxBootstrap()
